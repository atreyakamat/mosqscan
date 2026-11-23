# Vectora AI — Design System & Visual Specification

**Document Reference:** `reports/vectora_design_system.md`  
**Standard:** ASD-STE100 Technical English  
**Platforms:** Android (Jetpack Compose / Material3) & Web (Next.js 15 / React 19 / Tailwind CSS v4)  
**Status:** APPROVED FOR IMPLEMENTATION  

---

## 1. Product Design Direction

Vectora AI is a precision scientific technology platform for mosquito identification and vector surveillance. The user interface communicates intelligence, clinical precision, and scientific rigor.

### Key Visual Principles:
1. **Intelligent & Trustworthy:** Clean white and soft neutral surfaces that prioritize specimen photography and data clarity.
2. **Restrained Color Hierarchy:** Scientific teal and emerald accents for primary actions and confirmations; neutral slates for structures; warm amber for uncalibrated/experimental warnings.
3. **Structured Information Architecture:** Clear visual groupings with subtle borders and gentle shadows, avoiding visual noise or exaggerated gradients.
4. **Fluid Responsiveness:** Adaptive layouts optimized for handheld tablets (Samsung Galaxy Tab A7 Lite), mobile devices, and wide desktop displays.

---

## 2. Color Palette & Design Tokens

### 2.1 Core Palette

| Token Name | Hex Code | Android Compose Color | Web Tailwind Class | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `primary-teal` | `#0D9488` | `Color(0xFF0D9488)` | `text-teal-600`, `bg-teal-600` | Primary brand accent, main CTAs |
| `primary-teal-dark` | `#0F766E` | `Color(0xFF0F766E)` | `text-teal-700`, `bg-teal-700` | Hover states, active links |
| `primary-teal-light`| `#CCFBF1` | `Color(0xFFCCFBF1)` | `bg-teal-50`, `bg-teal-100` | Active selection, tag backgrounds |
| `background-light` | `#F8FAFC` | `Color(0xFFF8FAFC)` | `bg-slate-50` | Main application canvas |
| `surface-white` | `#FFFFFF` | `Color(0xFFFFFFFF)` | `bg-white` | Card and modal containers |
| `text-navy-charcoal`| `#0F172A` | `Color(0xFF0F172A)` | `text-slate-900` | Primary headings, specimen titles |
| `text-slate-body` | `#334155` | `Color(0xFF334155)` | `text-slate-700` | Body text, readable content |
| `text-slate-muted`| `#64748B` | `Color(0xFF64748B)` | `text-slate-500` | Supporting metadata, disclaimers |
| `border-subtle` | `#E2E8F0` | `Color(0xFFE2E8F0)` | `border-slate-200` | Container outlines, dividers |
| `warning-amber` | `#D97706` | `Color(0xFFD97706)` | `text-amber-600`, `bg-amber-50` | Experimental status, low scores |
| `error-rose` | `#E11D48` | `Color(0xFFE11D48)` | `text-rose-600`, `bg-rose-50` | Connection failure, invalid format |
| `success-emerald` | `#059669` | `Color(0xFF059669)` | `text-emerald-600`, `bg-emerald-50`| Confirmed identification, sync ok |

---

## 3. Typography & Hierarchy

### Android (Jetpack Compose Typography)
* **Title Large (Screen Headings):** 22sp, SemiBold, LineHeight 28sp.
* **Title Medium (Card Headings):** 16sp, SemiBold, LineHeight 22sp.
* **Body Large (Specimen Data, Instructions):** 14sp, Normal, LineHeight 20sp.
* **Body Medium (Supporting Content):** 12sp, Normal, LineHeight 16sp.
* **Label Small (Disclaimers, Badges, Scores):** 11sp, Medium, LineHeight 14sp.

### Web (Tailwind Typography)
* **H1 (Page Titles):** `text-3xl font-bold tracking-tight text-slate-900`
* **H2 (Section Titles):** `text-xl font-semibold text-slate-800`
* **H3 (Card Titles):** `text-base font-semibold text-slate-800`
* **Body:** `text-sm text-slate-600 leading-relaxed`
* **Captions & Meta:** `text-xs text-slate-500`

---

## 4. Reusable Component Specifications

### 4.1 Primary Buttons
* **Android:** `Button(colors = ButtonDefaults.buttonColors(containerColor = Teal600), shape = RoundedCornerShape(8.dp))`
* **Web:** `<Button className="bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-sm">`
* **Behavior:** Subtle touch press / active state, spinner state when request is pending, disabled state prevents duplicate submissions.

### 4.2 Scientific Status & Disclaimer Banner
* **Style:** Border-l-4 with tinted background, icon aligned to top-left.
* **Text:** `EXPERIMENTAL_NOT_FIELD_VALIDATED` displayed in uppercase bold.
* **Content:** Explicit statement that outputs are uncalibrated genus predictions from research models and must not be used for epidemiological decisions.

### 4.3 Scan Result Card
* **Header:** Specimen photo preview alongside predicted genus in bold display font.
* **Raw Score Breakdown:** All 3 genera (*Aedes*, *Anopheles*, *Culex*) rendered as progress bars with uncalibrated percentage values.
* **Action:** Prominent secondary action: "Explain with Vectora AI" (calls Gemma 3:4B).

### 4.4 Setup & Onboarding Wizard
* **Step Progression:** Linear indicator showing Step 1 through Step 5.
* **Server Verification:** Interactive test button with immediate visual feedback (server latency, model checksum status, assistant status).
* **Permissions Rationale:** Explicit user-facing justification before launching native dialogs.

---

## 5. Micro-Interactions & Usability

1. **Lightweight Transitions:** Smooth cross-fades and slide transitions between screens.
2. **Form Accessibility:** All text inputs possess visible labels and semantic screen-reader descriptions (`contentDescription` on Android, `aria-label` on Web).
3. **Contrast Compliance:** All text and interactive controls maintain WCAG 2.1 AA contrast ratios (minimum 4.5:1 for body text, 3:1 for large text).
4. **Reduced Motion:** Animations respect platform reduced-motion preferences.
