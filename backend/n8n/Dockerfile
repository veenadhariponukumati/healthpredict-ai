FROM n8nio/n8n:1.70.4

USER root
COPY --chmod=755 entrypoint.sh /docker-entrypoint-custom.sh
USER node

ENTRYPOINT ["tini", "--", "/docker-entrypoint-custom.sh"]
