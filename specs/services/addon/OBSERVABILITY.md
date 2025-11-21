# Service Observability Plan – addon

Describe the metrics, logs, and traces that prove this service is healthy. Inherit global goals from `../../platform/OBSERVABILITY.md` and add service-level KPIs here.

## Metrics
- **addons_ordered_total** (counter, dimensions: addon_type, is_admin): Add-on orders

## Logs
- Ensure `user_id`, `addon_type`, and `order_id` are included in structured logs.

## Traces
- **addon.order:** Add-on ordering (validation, fulfillment request, storage)
- **addon.fulfill:** Fulfillment processing (image generation, gallery update, notification)

## Alerts
- Alert on high failure rate for `addon.order` and `addon.fulfill`.
