"""
KI-Workflow für automatisches Immobilien-Videomarketing.

Dieses Paket enthält die Orchestrierungs- und Analyse-Logik für den
Reel-Automatisierungs-Workflow (siehe docs/video-automation/ARCHITEKTUR.md).
Die eigentliche Rohvideo-Verarbeitung läuft NICHT in Claude Code, sondern
auf einem separaten Worker (z. B. GPU-VM oder Modal/RunPod), der von n8n
angesteuert wird. Dieses Paket ist der Code, der auf diesem Worker läuft.
"""
