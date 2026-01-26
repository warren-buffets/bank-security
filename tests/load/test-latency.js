/**
 * SafeGuard Financial - Load Test for Latency
 *
 * Objective: Measure p95 latency under 1000 TPS sustained for 5 minutes
 * PSD2 Requirement: <100ms end-to-end latency
 * Tolerance: <200ms p95
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const latencyTrend = new Trend('custom_latency', true);

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 100 },   // Ramp-up to 100 VUs
    { duration: '1m', target: 500 },    // Ramp-up to 500 VUs
    { duration: '5m', target: 1000 },   // Sustain 1000 TPS for 5min
    { duration: '30s', target: 0 },     // Ramp-down
  ],

  thresholds: {
    // Critical: p95 latency must be <200ms (ideal <100ms)
    'http_req_duration': ['p(95)<200', 'p(99)<500'],

    // Error rate must be <1%
    'errors': ['rate<0.01'],

    // At least 80% of requests should succeed
    'checks': ['rate>0.8'],

    // HTTP failures <1%
    'http_req_failed': ['rate<0.01'],
  },

  // Summary export
  summaryTrendStats: ['min', 'avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

// Sample transaction payloads
const transactions = [
  // Legitimate transaction
  {
    event_id: 'evt_legit_',
    amount: 125.50,
    currency: 'EUR',
    merchant: { id: 'm123', mcc: '5411', country: 'FR' },
    card: { card_id: 'c123', type: 'physical', user_id: 'u123' },
    context: { ip: '1.2.3.4', geo: 'FR', channel: 'app' }
  },
  // Suspicious high amount
  {
    event_id: 'evt_high_',
    amount: 9500.00,
    currency: 'EUR',
    merchant: { id: 'm456', mcc: '5812', country: 'US' },
    card: { card_id: 'c456', type: 'virtual', user_id: 'u456' },
    context: { ip: '8.8.8.8', geo: 'US', channel: 'web' }
  },
  // Cross-border transaction
  {
    event_id: 'evt_cross_',
    amount: 450.00,
    currency: 'USD',
    merchant: { id: 'm789', mcc: '5411', country: 'CN' },
    card: { card_id: 'c789', type: 'physical', user_id: 'u789' },
    context: { ip: '192.168.1.1', geo: 'FR', channel: 'pos' }
  }
];

export default function () {
  // Select random transaction type
  const txIndex = Math.floor(Math.random() * transactions.length);
  const baseTx = transactions[txIndex];

  // Add unique event_id
  const payload = {
    ...baseTx,
    event_id: baseTx.event_id + __VU + '_' + __ITER
  };

  // Measure latency
  const startTime = new Date().getTime();

  const res = http.post(
    'http://localhost:8000/v1/score',
    JSON.stringify(payload),
    {
      headers: { 'Content-Type': 'application/json' },
      timeout: '10s',
    }
  );

  const endTime = new Date().getTime();
  const latency = endTime - startTime;

  // Record custom latency
  latencyTrend.add(latency);

  // Checks
  const checkResult = check(res, {
    'status is 200': (r) => r.status === 200,
    'has decision': (r) => r.json('decision') !== undefined,
    'has score': (r) => r.json('score') !== undefined,
    'latency <100ms (ideal)': () => latency < 100,
    'latency <200ms (acceptable)': () => latency < 200,
    'latency <500ms (tolerance)': () => latency < 500,
  });

  // Track errors
  errorRate.add(!checkResult);

  // Small think time to simulate realistic load
  sleep(0.1);
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'tests/load/results.json': JSON.stringify(data, null, 2),
  };
}

// Text summary helper
function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;

  let summary = '\n';
  summary += '======================================================================\n';
  summary += '                  SAFEGUARD LOAD TEST RESULTS\n';
  summary += '======================================================================\n\n';

  // HTTP metrics
  if (data.metrics.http_req_duration) {
    const duration = data.metrics.http_req_duration.values;
    summary += 'HTTP Request Duration:\n';
    summary += `${indent}  min: ${duration.min.toFixed(2)}ms\n`;
    summary += `${indent}  avg: ${duration.avg.toFixed(2)}ms\n`;
    summary += `${indent}  med: ${duration.med.toFixed(2)}ms\n`;
    summary += `${indent}  p90: ${duration['p(90)'].toFixed(2)}ms\n`;
    summary += `${indent}  p95: ${duration['p(95)'].toFixed(2)}ms `;

    if (duration['p(95)'] < 100) {
      summary += '✓ EXCELLENT (<100ms)\n';
    } else if (duration['p(95)'] < 200) {
      summary += '✓ ACCEPTABLE (<200ms)\n';
    } else {
      summary += '✗ EXCEEDS THRESHOLD (>200ms)\n';
    }

    summary += `${indent}  p99: ${duration['p(99)'].toFixed(2)}ms\n`;
    summary += `${indent}  max: ${duration.max.toFixed(2)}ms\n\n`;
  }

  // Throughput
  if (data.metrics.http_reqs) {
    const reqs = data.metrics.http_reqs.values;
    summary += `Total Requests: ${reqs.count}\n`;
    summary += `Requests/sec: ${reqs.rate.toFixed(2)}\n\n`;
  }

  // Error rate
  if (data.metrics.http_req_failed) {
    const failed = data.metrics.http_req_failed.values;
    summary += `Failed Requests: ${(failed.rate * 100).toFixed(2)}%\n\n`;
  }

  // Thresholds
  summary += 'Threshold Results:\n';
  for (const [name, threshold] of Object.entries(data.metrics)) {
    if (threshold.thresholds) {
      for (const [tname, result] of Object.entries(threshold.thresholds)) {
        const status = result.ok ? '✓ PASS' : '✗ FAIL';
        summary += `${indent}  ${status} - ${name}: ${tname}\n`;
      }
    }
  }

  summary += '\n======================================================================\n';

  return summary;
}
