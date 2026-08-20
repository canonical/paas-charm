/*
 * Copyright 2025 Canonical Ltd.
 * See LICENSE file for licensing details.
 */
const { NodeSDK } = require("@opentelemetry/sdk-node");
const {
  OTLPTraceExporter,
} = require("@opentelemetry/exporter-trace-otlp-proto");
const {
  getNodeAutoInstrumentations,
} = require("@opentelemetry/auto-instrumentations-node");
const {
  PrometheusExporter,
} = require("@opentelemetry/exporter-prometheus");

const metricsPath = process.env.METRICS_PATH || "/metrics";
const metricsPort = Number(process.env.METRICS_PORT || "9464");

const metricsExporter = new PrometheusExporter({
  endpoint: metricsPath,
  port: metricsPort,
});

const sdk = new NodeSDK({
  metricReader: metricsExporter,
  traceExporter: new OTLPTraceExporter(),
  instrumentations: [getNodeAutoInstrumentations()],
});

// Initialize the SDK
try {
  sdk.start();
  console.log(`Tracing initialized. Metrics exposed on port ${metricsPort} at ${metricsPath}`);
} catch (error) {
  console.log('Error initializing tracing', error);
}

// Graceful shutdown
process.on('SIGTERM', () => {
  sdk.shutdown()
    .then(() => console.log('Tracing terminated'))
    .catch((error) => console.log('Error terminating tracing', error))
    .finally(() => process.exit(0));
});
