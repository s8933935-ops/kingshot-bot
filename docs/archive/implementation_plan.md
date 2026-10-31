# Implementation Plan - Full Parameter Input Form matching kingshotsimulator.com

Build a complete parameter selection interface (Troop Tiers, FC Levels, Hero Select, Skill Levels) integrated with Screenshot OCR. This guarantees that exported JSON files satisfy 100% of `kingshotsimulator.com`'s validation rules with zero errors.

## 📋 Full Parameter Checklist

1. **Fighter Name**: Customizable text field (default "Player1").
2. **Stats (From Screenshot OCR or Manual Edit)**:
   - Infantry: Attack, Defense, Lethality, Health
   - Lancer (Cavalry): Attack, Defense, Lethality, Health
   - Archer (Marksman): Attack, Defense, Lethality, Health
3. **Troop Configurations**:
   - Tier (T1 to T10) for each troop type
   - FC (Fire Crystal) Level (0 to 5)
   - Troop Quantity / Count
4. **Hero Selection & Skills**:
   - Primary Hero Select (e.g. Jessica, Molly, Chenko, Amane, etc.)
   - Skill 1, Skill 2, Skill 3 Levels (1 to 5)

## Proposed Changes

### Web Application Updates

#### [MODIFY] [index.html](file:///C:/Users/s8933/.gemini/antigravity/brain/5bd109d2-e078-46ae-977d-3675e6326cf8/index.html)
- Add complete Form Sections for:
  - 1. Screenshot Upload (Fills Stats)
  - 2. Troop Config (Tier, FC Level, Quantity)
  - 3. Hero Config (Hero Select, Skill Levels)
  - 4. One-Tap Export JSON & Open Official Site

#### [MODIFY] [style.css](file:///C:/Users/s8933/.gemini/antigravity/brain/5bd109d2-e078-46ae-977d-3675e6326cf8/style.css)
- Mobile-friendly grid layouts for Troop Tier & Hero selection cards.

#### [MODIFY] [app.js](file:///C:/Users/s8933/.gemini/antigravity/brain/5bd109d2-e078-46ae-977d-3675e6326cf8/app.js)
- Full JSON Serializer populating all required keys (fighter_name, stats, troops, heroes, selected_heroes) based on user selections.

## Verification Plan

### Automated & Manual Verification
- Test JSON payload generation with full parameters.
- Verify generated JSON structure against `kingshotsimulator.com` requirements.
