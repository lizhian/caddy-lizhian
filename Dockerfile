# syntax=docker/dockerfile:1
ARG CADDY_BUILDER_IMAGE=caddy:builder
ARG CADDY_RUNTIME_IMAGE=caddy:alpine

FROM --platform=$BUILDPLATFORM ${CADDY_BUILDER_IMAGE} AS builder
ARG CADDY_VERSION=latest
ARG FORWARDPROXY_REF=latest
ARG CADDY_L4_REF=latest
ARG CLOUDFLARE_REF=latest
ARG TARGETOS
ARG TARGETARCH
ENV GOTOOLCHAIN=auto

RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    xcaddy build "${CADDY_VERSION}" --output /usr/bin/caddy \
      --with "github.com/caddyserver/forwardproxy@${FORWARDPROXY_REF}" \
      --with "github.com/mholt/caddy-l4@${CADDY_L4_REF}" \
      --with "github.com/caddy-dns/cloudflare@${CLOUDFLARE_REF}"

FROM ${CADDY_RUNTIME_IMAGE} AS runtime
ARG CADDY_VERSION=latest
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
COPY ci/ /tmp/caddy-ci/
RUN sh /tmp/caddy-ci/verify.sh "${CADDY_VERSION}" && rm -rf /tmp/caddy-ci

LABEL org.opencontainers.image.source="https://github.com/lizhian/lizhian-caddy" \
      org.opencontainers.image.title="lizhian-caddy" \
      org.opencontainers.image.description="Caddy with forwardproxy, caddy-l4 and Cloudflare DNS"
