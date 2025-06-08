# Product Requirements Document: Silero VAD Migration

**Document Version**: 1.0  
**Date**: January 8, 2025  
**Author**: System Architecture Team  
**Status**: Draft

## Executive Summary

This PRD outlines the migration from WebRTC VAD to Silero VAD for voice activity detection in our conversation system. Silero VAD offers superior accuracy, multi-language support, and neural network-based detection while maintaining real-time performance constraints.

## Background

### Current State
- Using WebRTC VAD with aggressiveness level 3
- Binary voice/no-voice detection
- 30ms frame processing at 16kHz
- Combined with dynamic audio level thresholding
- Dual VAD approach with WhisperKit's built-in VAD

### Limitations of Current Approach
1. **Accuracy**: WebRTC VAD uses simple spectral features, leading to false positives/negatives
2. **Language Coverage**: Optimized primarily for English speech patterns
3. **No Confidence Scores**: Binary output without probability estimates
4. **Fixed Parameters**: Limited configurability for different environments

## Objectives

### Primary Goals
1. **Improve Detection Accuracy**: Reduce false positives during noise and false negatives during soft speech
2. **Enhanced Language Support**: Better performance across 6000+ languages
3. **Confidence-Based Decisions**: Utilize probability scores for smarter interruption handling
4. **Maintain Real-Time Performance**: Keep processing under 5ms per frame

### Success Criteria
- VAD processing latency < 5ms per frame on M1 MacBook Air
- 95%+ accuracy on standard VAD benchmarks
- Seamless integration with existing interruption handler
- No regression in user experience

## Proposed Solution

### Technical Architecture

#### Core Components
1. **Silero VAD Model**
   - Use PyTorch JIT model (~2MB)
   - Support both 8kHz and 16kHz sampling rates
   - Process variable-length audio chunks

2. **Integration Points**
   ```
   Audio Input → Resampling (if needed) → Silero VAD → Probability Score → Interruption Logic
                                                     ↓
                                              Voice Timestamps → WhisperKit Coordination
   ```

3. **Configuration Parameters**
   ```python
   class SileroVADConfig:
       model_path: str = "silero_vad_v5.jit"
       sample_rate: int = 16000
       threshold: float = 0.5  # Probability threshold
       min_speech_duration: float = 0.25  # seconds
       min_silence_duration: float = 0.1  # seconds
       window_size_samples: int = 512  # ~32ms at 16kHz
       speech_pad_ms: int = 30  # Padding around speech
   ```

### Implementation Plan

#### Phase 1: Core Integration (Week 1)
1. Add Silero VAD dependencies to pyproject.toml
2. Create `SileroVADProcessor` class in `hello_world/utils/`
3. Implement model loading and caching
4. Add probability-based voice detection

#### Phase 2: Migration Path (Week 2)
1. Create feature flag for VAD selection
2. Implement adapter pattern for VAD backends
3. Add configuration for threshold tuning
4. Ensure backwards compatibility

#### Phase 3: Optimization (Week 3)
1. Implement batch processing for efficiency
2. Add voice activity smoothing
3. Optimize memory usage with circular buffers
4. Profile and tune performance

#### Phase 4: Testing & Rollout (Week 4)
1. Comprehensive unit tests
2. A/B testing framework
3. Performance benchmarking
4. Gradual rollout strategy

### API Design

```python
class VADProvider(Protocol):
    """Abstract interface for VAD implementations"""
    def process_frame(self, audio: np.ndarray) -> VADResult:
        ...
    
    def get_speech_timestamps(self, audio: np.ndarray) -> List[Timestamp]:
        ...

class VADResult:
    is_speech: bool
    probability: float
    timestamp: float
    
class SileroVADProvider(VADProvider):
    """Silero VAD implementation"""
    def __init__(self, config: SileroVADConfig):
        self.model = self._load_model(config.model_path)
        self.config = config
    
    def process_frame(self, audio: np.ndarray) -> VADResult:
        # Neural network inference
        probability = self.model(audio)
        return VADResult(
            is_speech=probability > self.config.threshold,
            probability=probability,
            timestamp=time.time()
        )
```

### Migration Strategy

1. **Parallel Running**: Run both VADs simultaneously, log differences
2. **Metrics Collection**: Track accuracy, latency, and resource usage
3. **Gradual Cutover**: Start with 5% traffic, increase based on metrics
4. **Rollback Plan**: Feature flag allows instant reversion

## Technical Requirements

### Dependencies
```toml
[project.dependencies]
silero-vad = ">=5.0"
torch = ">=1.12.0"  # CPU-only version
torchaudio = ">=0.12.0"
```

### Performance Requirements
- Model loading: < 500ms (one-time)
- Per-frame processing: < 5ms
- Memory usage: < 50MB additional
- CPU usage: < 5% on single core

### Compatibility
- Maintain existing `InterruptionHandler` interface
- Support same audio formats and sample rates
- Preserve metrics collection capabilities

## Risk Analysis

### Technical Risks
1. **Model Size**: 2MB model vs current lightweight implementation
   - *Mitigation*: Lazy loading, model quantization if needed

2. **PyTorch Dependency**: Adds ~100MB to deployment
   - *Mitigation*: Use ONNX runtime for smaller footprint

3. **Performance Regression**: Neural network overhead
   - *Mitigation*: Batch processing, caching, profiling

### Operational Risks
1. **User Experience**: Different VAD behavior may confuse users
   - *Mitigation*: Extensive testing, gradual rollout

2. **Platform Compatibility**: PyTorch availability on all platforms
   - *Mitigation*: Fallback to WebRTC VAD if needed

## Success Metrics

### Quantitative Metrics
- **Accuracy**: > 95% on test corpus
- **Latency**: p99 < 5ms per frame
- **False Positive Rate**: < 5% reduction from baseline
- **False Negative Rate**: < 10% reduction from baseline

### Qualitative Metrics
- User satisfaction with interruption handling
- Developer experience with new API
- System stability and reliability

## Timeline

- **Week 1**: Core integration and testing
- **Week 2**: Migration infrastructure  
- **Week 3**: Performance optimization
- **Week 4**: Testing and gradual rollout
- **Week 5**: Full deployment and monitoring

## Open Questions

1. Should we support ONNX runtime for smaller deployments?
2. How to handle the PyTorch dependency in containerized environments?
3. Should we implement custom training for domain-specific accuracy?
4. Integration with future speaker diarization features?

## Appendix

### Benchmark Comparison

| Metric | WebRTC VAD | Silero VAD |
|--------|------------|------------|
| Model Size | < 1KB | ~2MB |
| Latency | < 1ms | < 1ms |
| Languages | English-optimized | 6000+ |
| Accuracy | ~85% | ~97% |
| Output Type | Binary | Probability |
| Dependencies | None | PyTorch |

### References
- [Silero VAD Repository](https://github.com/snakers4/silero-vad)
- [WebRTC VAD Documentation](https://github.com/wiseman/py-webrtcvad)
- [Voice Activity Detection Benchmarks](https://github.com/snakers4/silero-vad#benchmarks)