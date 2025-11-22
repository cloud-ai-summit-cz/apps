import { trace, context, Span, SpanStatusCode } from '@opentelemetry/api';

/**
 * Utility module for creating custom spans and adding telemetry to application code.
 * Provides a simplified API for manual instrumentation.
 */

const tracer = trace.getTracer('web-frontend');

/**
 * Create a custom span for a specific operation.
 * Automatically ends the span when the callback completes.
 * 
 * @param name - Name of the span (e.g., "View Gallery", "Upload Avatar")
 * @param callback - Function to execute within the span context
 * @param attributes - Optional attributes to attach to the span
 * 
 * @example
 * ```ts
 * await withSpan('View Trip Gallery', async () => {
 *   const images = await tripApiClient.getGalleryImages(tripId);
 *   return images;
 * }, { trip_id: tripId, user_id: userId });
 * ```
 */
export async function withSpan<T>(
  name: string,
  callback: (span: Span) => Promise<T>,
  attributes?: Record<string, string | number | boolean>
): Promise<T> {
  const span = tracer.startSpan(name, {
    attributes,
  });

  return context.with(trace.setSpan(context.active(), span), async () => {
    try {
      const result = await callback(span);
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error instanceof Error ? error.message : String(error),
      });
      span.recordException(error as Error);
      throw error;
    } finally {
      span.end();
    }
  });
}

/**
 * Add custom attributes to the current active span.
 * Useful for enriching auto-instrumented spans with business context.
 * 
 * @param attributes - Key-value pairs to add to the current span
 * 
 * @example
 * ```ts
 * addSpanAttributes({
 *   user_id: user.oid,
 *   is_admin: user.roles.includes('Admin'),
 *   toy_id: toyId,
 * });
 * ```
 */
export function addSpanAttributes(attributes: Record<string, string | number | boolean>): void {
  const span = trace.getActiveSpan();
  if (span) {
    Object.entries(attributes).forEach(([key, value]) => {
      span.setAttribute(key, value);
    });
  }
}

/**
 * Record an event on the current active span.
 * Events represent specific points in time during span execution.
 * 
 * @param name - Name of the event
 * @param attributes - Optional attributes for the event
 * 
 * @example
 * ```ts
 * addSpanEvent('Image Upload Started', { filename: file.name, size: file.size });
 * ```
 */
export function addSpanEvent(name: string, attributes?: Record<string, string | number | boolean>): void {
  const span = trace.getActiveSpan();
  if (span) {
    span.addEvent(name, attributes);
  }
}

/**
 * Set the status of the current active span to error.
 * 
 * @param message - Error message
 * @param error - Optional error object to record
 * 
 * @example
 * ```ts
 * try {
 *   await apiCall();
 * } catch (error) {
 *   setSpanError('API call failed', error);
 *   throw error;
 * }
 * ```
 */
export function setSpanError(message: string, error?: Error): void {
  const span = trace.getActiveSpan();
  if (span) {
    span.setStatus({ code: SpanStatusCode.ERROR, message });
    if (error) {
      span.recordException(error);
    }
  }
}
