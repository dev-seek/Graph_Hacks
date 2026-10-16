"""Centre brain (spec §9 centre agent, §11.3, ADR-0014): read-mostly queries on the `centre` graph.

Every answer is a registry query (never free-form Cypher). The what-if copies the graph with
GRAPH.COPY and rescoring runs the normal Reasoner against the older and the newer kb.
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from collections.abc import Callable, Generator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from falkordb import FalkorDB, Graph
from pydantic import BaseModel, Field

from app.api import schemas as s
from app.engine.config import tuned_taus
from app.engine.reasoner import Reasoner
from app.engine.scoring import Finding
from app.graph.client import QueryLog, QueryLogEntry, rows, set_query_log, write
from app.llm.router import LLMRouter
from app.llm.schemas import TemplateChoice

CENTRE = "centre"
WHATIF = "centre_whatif"
ROOTS = frozenset({"HP:0000001", "HP:0000118"})
CASE_ID = re.compile(r"^C-\d{3}$")
TERM_ID = re.compile(r"^HP:\d{7}$")
KB_NAME = re.compile(r"^kb_\d{8}$")
MAX_TERMS = 40
MAX_NOTE = 500
WHATIF_THREADS = 8


class NotFound(LookupError):
    pass


class BadInput(ValueError):
    pass


class WhatIfDetail(BaseModel):
    case_id: str
    before: float
    after: float
    direction: str  # "crosses_up" | "crosses_down"


class WhatIfResult(BaseModel):
    from_version: str
    to_version: str
    tau2: float
    rescored: int
    details: list[WhatIfDetail]
    ms: float
    graph: str = WHATIF
    summary: str = ""
    cases: list[str] = Field(default_factory=list)


class Note(BaseModel):
    id: str
    text: str
    at: str
    role: str
    kind: str
    target: str


class Template(BaseModel):
    id: str
    description: str
    params: list[str]


TEMPLATES: tuple[Template, ...] = (
    Template(
        id="route_case",
        description="Who should take a given case and with which protocol",
        params=["case_id"],
    ),
    Template(id="bridges", description="Signs that link different groups of cases", params=[]),
    Template(id="clusters", description="Groups of similar cases in the clinic", params=[]),
    Template(id="protocols", description="Protocols used, how often, how fast", params=[]),
    Template(id="workload", description="Which clinician manages how many cases", params=[]),
    Template(id="overview", description="How many cases the centre holds", params=[]),
)
_TEMPLATE_IDS = {t.id: t for t in TEMPLATES}

_KEYWORDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bridges", re.compile(r"bridge|link|connect|common sign|key sign|central", re.I)),
    ("clusters", re.compile(r"cluster|group|communit|similar cases|families of cases", re.I)),
    ("protocols", re.compile(r"protocol|test|fast|turnaround|how long|slow|exome|panel", re.I)),
    ("workload", re.compile(r"who manages|clinician|workload|busy|specialist", re.I)),
)


def keyword_pick(question: str) -> TemplateChoice:
    """Deterministic fallback for the `centre_template_pick` task (spec §10)."""
    m = re.search(r"\bC-\d{3}\b", question)
    if m:
        return TemplateChoice(template_id="route_case", params={"case_id": m.group(0)})
    for tid, pattern in _KEYWORDS:
        if pattern.search(question):
            return TemplateChoice(template_id=tid)
    return TemplateChoice(template_id="overview")


def validate_choice(choice: TemplateChoice) -> None:
    """A model answer is only used if it names a whitelisted template with exactly its params."""
    tpl = _TEMPLATE_IDS.get(choice.template_id)
    if tpl is None:
        raise ValueError(f"unknown template {choice.template_id!r}")
    if set(choice.params) != set(tpl.params):
        raise ValueError(f"template {tpl.id} needs params {tpl.params}")
    if "case_id" in choice.params and not CASE_ID.match(choice.params["case_id"]):
        raise ValueError("case_id must look like C-123")


class CentreService:
    def __init__(
        self,
        db: FalkorDB,
        reasoner_for: Callable[[str], Reasoner],
        router: LLMRouter | None = None,
        ancestors: Mapping[str, set[str]] | None = None,
    ) -> None:
        self.db = db
        self.reasoner_for = reasoner_for
        self.router = router
        self.ancestors = ancestors
        self.log = QueryLog()
        self._mass: dict[tuple[str, tuple[str, ...]], float] = {}  # (kb, signs) -> rare mass

    @property
    def g(self) -> Graph:
        return self.db.select_graph(CENTRE)

    @contextmanager
    def logged(self) -> Generator[None]:
        set_query_log(self.log)
        try:
            yield
        finally:
            set_query_log(None)

    def inspector(self) -> list[s.QueryLogEntry]:
        return [
            s.QueryLogEntry(name=e.name, cypher=e.cypher, params=e.params, rows=e.rows, ms=e.ms)
            for e in self.log.entries[-40:]
        ]

    # ---- reads --------------------------------------------------------------------------------
    def overview(self) -> s.CentreOverview:
        with self.logged():
            r = rows(self.g, "c_overview", {})
        if not r:
            raise NotFound("centre graph not loaded")
        return s.CentreOverview(**{k: int(r[0][k]) for k in r[0]}, kb_version=self.kb_label())

    def kb_label(self) -> str:
        from app.kb.info import load_kb_info

        info = load_kb_info()
        return info.release if info else "unknown"

    def cases(self, status: str = "", limit: int = 50) -> list[dict[str, Any]]:
        if status not in ("", "open", "referred", "resolved"):
            raise BadInput("status must be open, referred or resolved")
        with self.logged():
            return rows(self.g, "c_cases_list", {"status": status, "limit": min(limit, 500)})

    def case(self, case_id: str) -> s.CentreCase:
        if not CASE_ID.match(case_id):
            raise NotFound(case_id)
        with self.logged():
            r = rows(self.g, "c_case", {"id": case_id})
            names = rows(self.g, "c_case_terms", {"id": case_id}) if r else []
        if not r:
            raise NotFound(case_id)
        x = r[0]
        return s.CentreCase(
            case_id=x["case_id"],
            status=x["status"],
            age_band=x["age_band"],
            terms=sorted(str(n["name"]) for n in names),
            diagnosis=x["diagnosis"],
        )

    def expand(self, term_ids: list[str]) -> list[str]:
        """Ancestor-closed term list (roots removed) for sign ids given by a caller."""
        ids = sorted({t for t in term_ids if TERM_ID.match(t)})[:MAX_TERMS]
        if not ids:
            return []
        if self.ancestors is not None:
            closed = {a for t in ids for a in self.ancestors.get(t, {t})}
        else:
            closed = {str(r["id"]) for r in rows(self.g, "c_term_ancestors", {"ids": ids})}
        return sorted(closed - ROOTS)

    def lookalikes_for(self, term_ids: list[str], exclude: str = "") -> list[s.CentreLookalike]:
        closed = self.expand(term_ids)
        return self._q7(closed, exclude)

    def _q7(self, closed: list[str], exclude: str) -> list[s.CentreLookalike]:
        if not closed:
            return []
        with self.logged():
            found = rows(self.g, "q7_centre_routing", {"terms": closed, "exclude": exclude})
        return [
            s.CentreLookalike(
                case_id=r["case_id"],
                diagnosis=r["diagnosis"],
                shared_terms=sorted(r["shared"])[:12],
                shared_ic=round(float(r["shared_ic"]), 2),
                clinician=r["clinician"],
                specialty=r["specialty"],
                protocol=r["protocol"],
                tests=list(r["tests"] or []),
                turnaround_days=r["turnaround_days"],
            )
            for r in found
        ]

    def routing(self, case_id: str) -> s.CentreRouting:
        if not CASE_ID.match(case_id):
            raise NotFound(case_id)
        with self.logged():
            anc = rows(self.g, "c_case_anc", {"id": case_id})
        if not anc:
            raise NotFound(case_id)
        look = self._q7(sorted(str(r["id"]) for r in anc), case_id)
        return s.CentreRouting(case_id=case_id, lookalikes=look, **suggest(look))

    def bridges(self) -> list[s.CentreBridge]:
        with self.logged():
            r = rows(self.g, "q8a_bridges", {})
        return [
            s.CentreBridge(term_id=x["term"], name=x["name"], score=round(float(x["score"]), 1))
            for x in r
        ]

    def clusters(self, method: str = "lp") -> list[s.CentreCluster]:
        if method not in ("lp", "wcc"):
            raise BadInput("method must be lp or wcc")
        with self.logged():
            r = rows(self.g, "q8c_label_propagation" if method == "lp" else "q8b_wcc", {})
        out = [
            s.CentreCluster(
                cluster_id=int(x["componentId" if method == "wcc" else "communityId"]),
                cases=sorted(x["cases"]),
                size=int(x["size"]),
            )
            for x in r
            if int(x["size"]) >= 2
        ]
        return out

    def protocols(self) -> list[dict[str, Any]]:
        with self.logged():
            return rows(self.g, "c_protocol_stats", {})

    def workload(self) -> list[dict[str, Any]]:
        with self.logged():
            return rows(self.g, "c_clinician_stats", {})

    # ---- notes --------------------------------------------------------------------------------
    def add_note(self, kind: str, target: str, text: str, role: str = "clinician") -> Note:
        text = " ".join(text.split())[:MAX_NOTE]
        if not text:
            raise BadInput("note is empty")
        if kind not in ("case", "term", "protocol"):
            raise BadInput("kind must be case, term or protocol")
        ok = {"case": CASE_ID, "term": TERM_ID, "protocol": re.compile(r"^PR-\d$")}[kind]
        if not ok.match(target):
            raise BadInput(f"bad {kind} id")
        nid = f"N-{int(time.time() * 1000)}"
        at = datetime.now(UTC).isoformat(timespec="seconds")
        with self.logged():
            made = write(
                self.g,
                f"c_add_note_{kind}",
                {"id": nid, "text": text, "at": at, "role": role[:40], "target": target},
            )
        if not made:
            raise NotFound(target)
        return Note(id=nid, text=text, at=at, role=role, kind=kind, target=target)

    def notes(self, target: str = "") -> list[Note]:
        with self.logged():
            r = rows(self.g, "c_notes", {"target": target})
        return [Note(**x) for x in r]

    # ---- what-if ------------------------------------------------------------------------------
    def whatif(self, new_kb: str, tau2: float | None = None) -> WhatIfResult:
        if not KB_NAME.match(new_kb) or new_kb not in self.db.list_graphs():
            raise BadInput("unknown knowledge-base version")
        tau = tau2 if tau2 is not None else tuned_taus().t2
        t0 = time.perf_counter()
        with self.logged():
            open_rows = rows(self.g, "c_open_cases", {})
        if not open_rows:
            raise NotFound("no open cases")
        old_kb = str(open_rows[0]["kb_version"])
        copy_t = time.perf_counter()
        try:
            self.db.select_graph(WHATIF).delete()
        except Exception:  # noqa: BLE001, S110 (nothing to delete the first time)
            pass
        self.g.copy(WHATIF)
        self.log.add(
            QueryLogEntry("GRAPH.COPY", f"GRAPH.COPY {CENTRE} {WHATIF}", {}, 0, _ms(copy_t))
        )
        before = self._rare_masses(old_kb, open_rows)
        after = self._rare_masses(new_kb, open_rows)
        details: list[WhatIfDetail] = []
        for r in open_rows:
            cid = str(r["case_id"])
            b, a = before[cid], after[cid]
            if b < tau <= a:
                details.append(WhatIfDetail(case_id=cid, before=b, after=a, direction="crosses_up"))
            elif a < tau <= b:
                details.append(
                    WhatIfDetail(case_id=cid, before=b, after=a, direction="crosses_down")
                )
        wg = self.db.select_graph(WHATIF)
        with self.logged():
            write(
                wg,
                "c_whatif_update_cases",
                {
                    "to": new_kb,
                    "rows": [
                        {
                            "c": str(r["case_id"]),
                            "prev": before[str(r["case_id"])],
                            "now": after[str(r["case_id"])],
                        }  # fmt: skip
                        for r in open_rows
                    ],
                },
            )
            write(
                wg,
                "c_whatif_kbupdate",
                {
                    "from": old_kb,
                    "to": new_kb,
                    "at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "tau2": tau,
                    "cases": [d.case_id for d in details],
                },
            )
        up = sum(d.direction == "crosses_up" for d in details)
        down = len(details) - up
        summary = (
            f"{len(open_rows)} open cases rescored on {new_kb} (were on {old_kb}); "
            f"{up} now reach rare-disease mass >= {tau:.2f}, {down} fall below it."
        )
        return WhatIfResult(
            from_version=old_kb,
            to_version=new_kb,
            tau2=tau,
            rescored=len(open_rows),
            details=details,
            ms=_ms(t0),
            summary=summary,
            cases=[d.case_id for d in details],
        )

    def _rare_masses(self, kb: str, open_rows: list[dict[str, Any]]) -> dict[str, float]:
        reasoner = self.reasoner_for(kb)

        def one(r: dict[str, Any]) -> tuple[str, float]:
            terms = tuple(sorted(str(t) for t in r["terms"]))
            key = (kb, terms)
            if key not in self._mass:
                findings = [Finding(t, "present", "doctor_exam") for t in terms]
                _, res = reasoner.score(findings) if findings else ([], None)
                self._mass[key] = round(float(res.rare_mass), 4) if res else 0.0
            return str(r["case_id"]), self._mass[key]

        with ThreadPoolExecutor(WHATIF_THREADS) as pool:
            return dict(pool.map(one, open_rows))

    # ---- ask the centre -----------------------------------------------------------------------
    def pick(self, question: str) -> tuple[TemplateChoice, str]:
        """(template, source): the model's choice if it validates, else keywords."""
        if self.router is None:
            return keyword_pick(question), "fallback"
        payload = json.dumps(
            {"question": question, "templates": [t.model_dump() for t in TEMPLATES]}
        )
        res = self.router.run(
            "centre_template_pick",
            payload,
            TemplateChoice,
            lambda: keyword_pick(question),
            validate=validate_choice,
        )
        return res.value, res.source

    def ask(self, question: str) -> s.CentreAskOut:
        choice, _ = self.pick(question)
        validate_choice(choice)  # also guards the fallback
        tid = choice.template_id
        if tid == "route_case":
            cid = choice.params["case_id"]
            r = self.routing(cid)
            if not r.lookalikes:
                return s.CentreAskOut(answer=f"No solved look-alikes for {cid}.", query_ids=["q7"])
            who = r.suggested_clinician or "no clinician"
            how = r.suggested_protocol or "no protocol"
            days = f" (about {r.expected_days} days)" if r.expected_days else ""
            answer = (
                f"For {cid}: {who} ({r.suggested_specialty}) solved the closest look-alikes; "
                f"the usual protocol was {how}{days}."
            )
            return s.CentreAskOut(answer=answer, query_ids=["c_case_anc", "q7_centre_routing"])
        if tid == "bridges":
            b = self.bridges()[:5]
            names = ", ".join(x.name for x in b)
            return s.CentreAskOut(
                answer=f"Signs that connect the most groups of cases: {names}.",
                query_ids=["q8a_bridges"],
            )
        if tid == "clusters":
            c = self.clusters("lp")
            return s.CentreAskOut(
                answer=f"{len(c)} groups of similar cases; the largest has {c[0].size} cases."
                if c
                else "No groups found.",
                query_ids=["q8c_label_propagation"],
            )
        if tid == "protocols":
            p = self.protocols()
            if not p:
                return s.CentreAskOut(
                    answer="No protocols recorded.", query_ids=["c_protocol_stats"]
                )
            fast = p[0]
            top = max(p, key=lambda x: x["cases"])
            return s.CentreAskOut(
                answer=(
                    f"Fastest on average: {fast['protocol']} ({fast['avg_days']:.0f} days). "
                    f"Most used: {top['protocol']} ({top['cases']} cases)."
                ),
                query_ids=["c_protocol_stats"],
            )
        if tid == "workload":
            w = self.workload()
            text = "; ".join(f"{x['clinician']} ({x['specialty']}): {x['cases']}" for x in w[:7])
            return s.CentreAskOut(answer=f"Cases managed: {text}.", query_ids=["c_clinician_stats"])
        o = self.overview()
        return s.CentreAskOut(
            answer=f"The centre holds {o.cases} illustrative cases ({o.resolved} solved).",
            query_ids=["c_overview"],
        )


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def suggest(look: list[s.CentreLookalike]) -> dict[str, Any]:
    """Clinician and protocol that solved the closest look-alikes (weighted by shared IC)."""
    who: defaultdict[tuple[str, str], float] = defaultdict(float)
    how: defaultdict[str, float] = defaultdict(float)
    tests: dict[str, list[str]] = {}
    days: dict[str, list[int]] = defaultdict(list)
    for x in look:
        if x.clinician:
            who[(x.clinician, x.specialty or "")] += x.shared_ic
        if x.protocol:
            how[x.protocol] += x.shared_ic
            tests[x.protocol] = x.tests
            if x.turnaround_days:
                days[x.protocol].append(x.turnaround_days)
    out: dict[str, Any] = {}
    if who:
        (clin, spec) = max(who, key=lambda k: who[k])
        out |= {"suggested_clinician": clin, "suggested_specialty": spec}
    if how:
        proto = max(how, key=lambda k: how[k])
        d = days.get(proto)
        out |= {
            "suggested_protocol": proto,
            "suggested_tests": tests[proto],
            "expected_days": round(sum(d) / len(d)) if d else None,
        }
    return out
