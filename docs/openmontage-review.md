# Review: OpenMontage (calesthio/OpenMontage)

Kurzreview des Repos [`calesthio/OpenMontage`](https://github.com/calesthio/OpenMontage) im Hinblick auf mögliche Relevanz für dieses Projekt (Melkyab-Bot / Immobilien-Analyzer).

## Was es ist

OpenMontage ist ein **agentisches Video-Produktionssystem**, kein eigenständiges Tool. Es gibt keinen klassischen Code-Orchestrator — ein KI-Coding-Assistent (Claude Code, Cursor, Copilot, Windsurf, Codex) liest YAML-Pipeline-Manifeste und Markdown-„Skills“ und steuert damit >100 Python-Tools, um aus einem Text-Prompt ein fertig geschnittenes Video zu produzieren (Recherche → Skript → Storyboard → Asset-Generierung → Schnitt → Rendering).

**Ablauf jeder Pipeline:**
```
research -> proposal -> script -> scene_plan -> assets -> edit -> compose
```

## Architektur (Kernpunkte)

- `pipeline_defs/*.yaml` — 10+ Pipelines (Animated Explainer, Documentary Montage, Cinematic, Talking Head, Screen Demo, Podcast Repurpose, Localization/Dub, Clip Factory, Avatar Spokesperson, Hybrid, Character Animation)
- `tools/` — 100+ registrierte Tools (Video/Bild-Generierung, TTS, Musik, Subtitle, Enhancement, Analyse), Provider-Anbindung über eine **7-Dimensionen-Scoring-Engine** (Task Fit, Qualität, Kontrolle, Zuverlässigkeit, Kosten, Latenz, Kontinuität)
- `skills/` — Markdown-Anleitungen, die dem Agenten erklären, *wie* jede Stufe auszuführen ist
- `remotion-composer/` — React/Remotion-Renderer; `ink-theater/` — HTML/CSS/GSAP-Renderer ("HyperFrames")
- `backlot/` — lokales Live-Dashboard (Storyboard, Freigabe-Gates, Kostenanzeige)
- Qualitäts-Gates: Pre-Compose-Validierung, Post-Render-Self-Review (ffprobe, Frame-Sampling, Audioanalyse), Slideshow-Risk-Scoring, Budget-Caps

**Kostenlos nutzbar** (ohne API-Keys): Piper TTS (Offline-Sprachausgabe), freie Stock-/Archivquellen (Archive.org, NASA, Wikimedia, Pexels/Pixabay mit Gratis-Key), FFmpeg, Remotion. Mit API-Keys kommen Anbieter wie Kling, Veo, Runway, ElevenLabs, Suno etc. dazu.

## Lizenz — wichtig

**AGPLv3.** Das ist strenges Copyleft mit Network-Use-Klausel: Wird der Code (auch nur als Backend eines Dienstes, ohne Distribution der Binaries) für Nutzer über ein Netzwerk erreichbar gemacht, muss der vollständige Quellcode inkl. eigener Änderungen offengelegt werden. Eine Einbindung in einen closed-source/kommerziellen Bot-Betrieb wäre lizenzrechtlich heikel und sollte vor produktivem Einsatz geprüft werden (ggf. rechtliche Beratung oder Trennung als eigenständiger, separat lizenzierter Dienst).

## Relevanz für dieses Projekt

Dieses Repo (`melkyab-bot`) betreibt aktuell:
- einen Telegram-Kreditrechner-Bot (Farsi) für Immobilienfinanzierung
- einen täglichen Immobilien-Scraper/Analyzer (ImmoScout24, Kleinanzeigen) mit statischem Report unter `docs/`

Denkbare Berührungspunkte mit OpenMontage:
- **Automatisierte Video-Reels aus Objektdaten**: die `immobilien_analyzer`-Ergebnisse (Adresse, Preis, Fotos) könnten als Input für eine "Cinematic"- oder "Documentary Montage"-Pipeline dienen, um automatisch kurze Objekt-Videos für Social Media zu erzeugen — ähnlich wie das bereits vorhandene `remotion-property-reels`-Skill-Konzept in diesem Account, nur agentisch statt direkt über MCP gesteuert.
- Der Ansatz ist aber **schwergewichtig**: Python 3.10+, Node 18+, FFmpeg, eigenes Pipeline-/Skill-System — kein leichtgewichtiges Modul, das man einfach importiert. Eine Integration würde faktisch bedeuten, OpenMontage als eigenständiges Projekt danebenzustellen und per Automatisierung (z.B. n8n, Cronjob) anzusteuern, nicht als Library in `melkyab-bot` einzubinden.
- Für den aktuellen Bot-Scope (Kreditrechner, Immobilien-Report) besteht kein unmittelbarer Bedarf; relevant wäre es eher für ein zukünftiges Marketing-/Content-Vorhaben (Video-Ads für Objekte), vergleichbar mit den vorhandenen Skills `remotion-property-reels` und `higgsfield-content-factory`.

## Fazit

Solides, gut dokumentiertes Open-Source-Projekt für agentische Video-Produktion mit durchdachten Qualitäts-Gates und breiter Provider-Unterstützung. Für eine Direkt-Integration in `melkyab-bot` aktuell nicht notwendig; bei Interesse an automatisierten Objekt-Video-Reels wäre es ein separates Vorhaben — unter Beachtung der AGPLv3-Lizenzpflichten.
