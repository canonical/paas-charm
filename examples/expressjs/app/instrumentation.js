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

const metricsExporter = new PrometheusExporter({
  endpoint: process.env.METRICS_PATH || "/metrics",
  port: Number(process.env.METRICS_PORT || "9464"),
});

const sdk = new NodeSDK({
  metricReader: metricsExporter,
  traceExporter: new OTLPTraceExporter(),
  metricReader: prometheusExporter, // Add the configured exporter here
  instrumentations: [getNodeAutoInstrumentations()],
});

// Initialize the SDK
sdk.start()
  .then(() => console.log(`Tracing initialized. Metrics exposed on port ${metricsPort} at ${metricsPath}`))
  .catch((error) => console.log('Error initializing tracing', error));

// Graceful shutdown
process.on('SIGTERM', () => {
  sdk.shutdown()
    .then(() => console.log('Tracing terminated'))
    .catch((error) => console.log('Error terminating tracing', error))
    .finally(() => process.exit(0));
});

