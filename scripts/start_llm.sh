#!/bin/bash
# Start llama-server with Gemma 3 27B (vision capable)
# GPU offload (RTX 3070) + CPU (Ryzen 9 128GB RAM)

LLAMA_SERVER="/home/adminator/llama.cpp/build/bin/llama-server"
MODEL="/home/adminator/llama.cpp/text-models/gemma3_27b/gemma-3-27b-it-UD-Q8_K_XL/gemma-3-27b-it-UD-Q8_K_XL.gguf"
# Vision projector for multimodal (optional - uncomment to enable)
# MMPROJ="/home/adminator/llama.cpp/text-models/gemma3_27b/mmproj-F16.gguf"
PORT=8084

# GPU layers to offload (RTX 3070 has 8GB VRAM)
# Q8 27B model is ~30GB - can fit more layers with smaller quant
# Start conservative, increase if VRAM allows
GPU_LAYERS=28

# Threads for CPU processing
THREADS=16

# Context size (Gemma 3 supports up to 128k, but use less for speed)
CTX_SIZE=8192

echo "Starting llama-server..."
echo "Model: Gemma 3 27B IT (Q8_K_XL)"
echo "Path: $MODEL"
echo "Port: $PORT"
echo "GPU Layers: $GPU_LAYERS"
echo "Threads: $THREADS"
echo "Context: $CTX_SIZE"
echo ""

# Check if model exists
if [ ! -f "$MODEL" ]; then
    echo "ERROR: Model not found at $MODEL"
    exit 1
fi

# Check if llama-server exists
if [ ! -f "$LLAMA_SERVER" ]; then
    echo "ERROR: llama-server not found at $LLAMA_SERVER"
    exit 1
fi

# Set library path
export LD_LIBRARY_PATH="/home/adminator/llama.cpp/build/bin:$LD_LIBRARY_PATH"

# Start server
# Add --mmproj "$MMPROJ" below if enabling vision
exec "$LLAMA_SERVER" \
    --model "$MODEL" \
    --port "$PORT" \
    --host 0.0.0.0 \
    --n-gpu-layers "$GPU_LAYERS" \
    --threads "$THREADS" \
    --ctx-size "$CTX_SIZE" \
    --parallel 2 \
    --cont-batching \
    --flash-attn on
