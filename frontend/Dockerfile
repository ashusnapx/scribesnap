# =============================================================================
# ScribeSnap Frontend Dockerfile
# =============================================================================
# What:  Multi-stage Docker build for Next.js 14 frontend.
# Why:   Produces a minimal production image (~100MB vs ~1GB).
# How:   Uses Next.js "standalone" output mode.
# When:  Built by docker-compose or CI/CD pipeline.
#
# Stages:
#   1. deps: Install dependencies only (cached)
#   2. builder: Build the Next.js application
#   3. runner: Minimal runtime image
# =============================================================================

# ── Stage 1: Dependencies ────────────────────────────────────────────────
FROM node:18-alpine AS deps
# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine to understand why libc6-compat might be needed.
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies based on lockfile
RUN \
  if [ -f package-lock.json ]; then npm ci; \
  else echo "Lockfile not found." && exit 1; \
  fi


# ── Stage 2: Builder ─────────────────────────────────────────────────────
FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment to production
ENV NEXT_TELEMETRY_DISABLED 1

# Build the application
# This will create the .next/standalone directory
RUN npm run build


# ── Stage 3: Runtime ─────────────────────────────────────────────────────
FROM node:18-alpine AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
# public folder for static assets
COPY --from=builder /app/public ./public

# Set permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverage output traces to reduce image size
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
# server.js is created by next build from the standalone output
# https://nextjs.org/docs/pages/api-reference/next-config-js/output
CMD ["node", "server.js"]
