import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { Resource } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from '@opentelemetry/semantic-conventions';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction';
import { SamplingDecision } from '@opentelemetry/sdk-trace-base';

/**
 * Initialize OpenTelemetry for the browser.
 * Sets up trace provider, instrumentations, and exporter to send telemetry
 * to the OTEL collector via the Nginx proxy endpoint.
 */
export async function initializeTelemetry(): Promise<void> {
  try {
    // Get environment-specific configuration
    const environment = window.ENV_CONFIG?.ENVIRONMENT || 'development';
    const serviceName = 'web-frontend';
    const serviceVersion = window.ENV_CONFIG?.SERVICE_VERSION || '1.0.0';

    console.log('[Telemetry] Starting initialization...', {
      environment,
      serviceName,
      serviceVersion,
      hasEnvConfig: !!window.ENV_CONFIG,
    });

    // Determine sampling rate based on environment
    // Production: 10% sampling to reduce volume
    // Dev/Staging: 100% sampling for debugging
    const samplingRate = environment === 'production' ? 0.1 : 1.0;

    // Create resource with service metadata
    const resource = Resource.default().merge(
      new Resource({
        [ATTR_SERVICE_NAME]: serviceName,
        [ATTR_SERVICE_VERSION]: serviceVersion,
        'deployment.environment': environment,
      })
    );

    // Create tracer provider
    const provider = new WebTracerProvider({
      resource,
      // Simple probability-based sampler
      sampler: {
        shouldSample: () => ({
          decision: Math.random() < samplingRate ? SamplingDecision.RECORD_AND_SAMPLED : SamplingDecision.NOT_RECORD,
          attributes: {},
        }),
        toString: () => `ProbabilitySampler{${samplingRate}}`,
      },
    });

    // Configure OTLP exporter to send to Nginx proxy endpoint
    // This endpoint requires authentication (session cookie)
    const exporter = new OTLPTraceExporter({
      url: '/otel/v1/traces', // Relative URL - proxied by Nginx
      headers: {
        'Content-Type': 'application/json',
      },
    });

    console.log('[Telemetry] OTLP Exporter configured with URL:', '/otel/v1/traces');

    // Use batch processor to reduce network overhead
    provider.addSpanProcessor(
      new BatchSpanProcessor(exporter, {
        maxQueueSize: 100,
        maxExportBatchSize: 10,
        scheduledDelayMillis: 5000, // Export every 5 seconds
      })
    );

    console.log('[Telemetry] Batch span processor added (5s interval)');

    // Register the provider globally
    provider.register({
      contextManager: new ZoneContextManager(),
    });

    console.log('[Telemetry] Tracer provider registered globally');

    // Register instrumentations for automatic tracing
    registerInstrumentations({
      instrumentations: [
        // Document load instrumentation - traces page load performance
        new DocumentLoadInstrumentation(),
        
        // Fetch instrumentation - traces HTTP requests
        // Propagates trace context to backend services via traceparent header
        new FetchInstrumentation({
          // Propagate trace context to all API calls on the same origin
          // This enables distributed tracing: frontend span -> backend span correlation
          propagateTraceHeaderCorsUrls: [
            /.*/, // Propagate to all URLs (same-origin + configured CORS)
          ],
          clearTimingResources: true,
          // Don't trace the OTEL endpoint itself to avoid recursion
          ignoreUrls: [/\/otel\/v1\/traces/],
        }),
        
        // User interaction instrumentation - traces clicks and other interactions
        new UserInteractionInstrumentation({
          eventNames: ['click', 'submit'],
        }),
      ],
    });

    console.log('[Telemetry] Instrumentations registered:', [
      'DocumentLoadInstrumentation',
      'FetchInstrumentation',
      'UserInteractionInstrumentation',
    ]);

    console.info('[Telemetry] OpenTelemetry initialized successfully', {
      serviceName,
      serviceVersion,
      environment,
      samplingRate: `${samplingRate * 100}%`,
      exporterUrl: '/otel/v1/traces',
    });

    // Create a test span to verify the pipeline is working
    const { trace } = await import('@opentelemetry/api');
    const tracer = trace.getTracer('web-frontend');
    const testSpan = tracer.startSpan('app.initialization');
    testSpan.setAttribute('test', true);
    testSpan.setAttribute('environment', environment);
    testSpan.end();
    console.log('[Telemetry] Test span created and ended');
  } catch (error) {
    console.error('[Telemetry] Failed to initialize OpenTelemetry:', error);
  }
}

/**
 * Shutdown telemetry and flush pending spans.
 * Should be called when the application is closing (e.g., beforeunload).
 */
export async function shutdownTelemetry(): Promise<void> {
  try {
    // Import here to avoid circular dependency
    const { trace } = await import('@opentelemetry/api');
    const provider = trace.getTracerProvider() as WebTracerProvider;
    
    if (provider && typeof provider.shutdown === 'function') {
      await provider.shutdown();
      console.info('[Telemetry] OpenTelemetry shutdown complete');
    }
  } catch (error) {
    console.error('[Telemetry] Error during shutdown:', error);
  }
}
