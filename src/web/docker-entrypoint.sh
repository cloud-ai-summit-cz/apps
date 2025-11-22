#!/bin/sh
set -e

# Generate env-config.js from environment variables
cat > /usr/share/nginx/html/env-config.js <<EOF
window.ENV_CONFIG = {
  TOY_SERVICE_URL: '${TOY_SERVICE_URL:-http://localhost:8001}',
  TRIP_SERVICE_URL: '${TRIP_SERVICE_URL:-http://localhost:8002}',
  DEMO_DATA_API_URL: '${DEMO_DATA_API_URL:-http://localhost:8010}',
  MSAL_REDIRECT_URI: '${MSAL_REDIRECT_URI:-http://localhost:3000}',
  OTEL_COLLECTOR_URL: '${OTEL_COLLECTOR_URL:-http://otel-collector:4318}',
  ENVIRONMENT: '${ENVIRONMENT:-development}',
  SERVICE_VERSION: '${SERVICE_VERSION:-1.0.0}',
};
EOF

echo "Generated env-config.js with:"
echo "  TOY_SERVICE_URL: ${TOY_SERVICE_URL:-http://localhost:8001}"
echo "  TRIP_SERVICE_URL: ${TRIP_SERVICE_URL:-http://localhost:8002}"
echo "  DEMO_DATA_API_URL: ${DEMO_DATA_API_URL:-http://localhost:8010}"
echo "  MSAL_REDIRECT_URI: ${MSAL_REDIRECT_URI:-http://localhost:3000}"
echo "  OTEL_COLLECTOR_URL: ${OTEL_COLLECTOR_URL:-http://otel-collector:4318}"
echo "  ENVIRONMENT: ${ENVIRONMENT:-development}"
echo "  SERVICE_VERSION: ${SERVICE_VERSION:-1.0.0}"

# Export OTEL_COLLECTOR_URL with default value for envsubst
export OTEL_COLLECTOR_URL="${OTEL_COLLECTOR_URL:-http://otel-collector:4318}"

# Substitute environment variables in nginx.conf
envsubst '${OTEL_COLLECTOR_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

echo "Configured nginx with OTEL_COLLECTOR_URL: ${OTEL_COLLECTOR_URL}"

# Execute the main container command (nginx)
exec "$@"
