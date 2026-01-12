---
description: AI rules derived by SpecStory from the project AI interaction history
globs: *
---

## HEADERS

## TECH STACK

## PROJECT DOCUMENTATION & CONTEXT SYSTEM

## CODING STANDARDS

## WORKFLOW & RELEASE RULES

## DEBUGGING

## HOME ASSISTANT INTEGRATION QUALITY VERIFICATION

When assessing the quality of Home Assistant integrations, especially custom HACS integrations, remember the following:

*   **Quality Scale Applicability:** The official Home Assistant quality scale system primarily applies to core integrations within the `homeassistant/components/` directory of the main Home Assistant repository and those that explicitly declare a quality tier (Bronze, Silver, Gold, or Platinum) in their `manifest.json`.

*   **Custom Component Considerations:** Custom components distributed through HACS are not required to adhere to the official quality scale rules. However, they can still be assessed against quality scale best practices.

*   **Assessment Options:** Offer the following assessment options:

    1.  **Specific Rule Verification:** Verify compliance with specific quality scale rules (e.g., `config-flow`, `entity-unique-id`, `test-before-setup`) to evaluate the integration's adherence to core integration standards.

    2.  **General Quality Assessment:** Review the code for general best practices, common issues, and Home Assistant conventions.

    3.  **Quality Scale Tracking Setup:** Assist in setting up a `quality_scale.yaml` file to track the integration's compliance with quality scale rules, facilitating eventual core integration or maintaining high quality.

*   **Initial Checks:** Begin by examining the integration to determine:

    1.  Whether it declares a quality scale in `manifest.json`.

    2.  If a `quality_scale.yaml` file exists.

    3.  The general structure and compliance of the integration.

*   **No Declaration Handling:** If the integration doesn't declare a quality scale in `manifest.json` and lacks a `quality_scale.yaml` file, explicitly state that it does not participate in the official quality scale system.

## REFERENCES