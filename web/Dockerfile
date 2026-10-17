# Next.js app. API_ORIGIN is baked into the /api rewrite at build time (next.config.ts).
FROM node:22.23.3-alpine AS build
RUN npm install -g pnpm@12.11.2
WORKDIR /app
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
ARG API_ORIGIN=http://api:8000
ENV API_ORIGIN=$API_ORIGIN NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM node:22.23.3-alpine
RUN npm install -g pnpm@12.11.2
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app ./
USER node
EXPOSE 3000
CMD ["pnpm", "exec", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
