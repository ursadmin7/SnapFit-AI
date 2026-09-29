# Performance

## Current State

Pose inference and exercise calculations run on the local machine using MediaPipe Tasks and OpenCV. The application requests a 960x540 camera frame for the exercise analyzers. No repeatable latency, throughput, memory, or power benchmark is currently recorded; benchmarking is pending.

## Snapdragon Status

Snapdragon Windows PCs are a target platform, not a verified accelerator configuration. This project does not currently prove that inference executes on a Qualcomm NPU. Do not infer NPU usage from local execution or the presence of a Snapdragon processor.

## Benchmark Plan

Record the exact PC model, processor, operating system, Python and dependency versions, model asset, camera resolution, warm-up period, sample count, and test conditions. Measure end-to-end frame latency and steady-state FPS, plus startup time and memory. Repeat across the available CPU/GPU configuration and any supported Snapdragon NPU runtime. Keep raw measurements and report median and tail latency; do not publish estimates as measured results.

## Optimization Path

Profile the current MediaPipe Tasks path first. Then evaluate Qualcomm AI Hub model optimization and a supported Snapdragon inference provider on target hardware. Preserve a CPU fallback and compare pose quality as well as speed before choosing a deployment configuration.