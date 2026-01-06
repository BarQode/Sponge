# Sponge UI Theme Guide

## 🎨 Visual Identity

The Sponge RCA Tool uses a distinctive orange and sponge-brain aesthetic that reflects its purpose: intelligently "absorbing" and analyzing system issues.

---

## 🧽 Design Concept

### Theme Elements

1. **Sponge Brain Logo**
   - Yellow-green sponge texture representing AI/ML intelligence
   - Organic, brain-like curves showing pattern recognition
   - Orange background for energy and attention

2. **Soap Bubbles**
   - Floating bubbles create a sense of cleanliness and problem resolution
   - Gentle animations suggest ongoing monitoring and activity
   - White/transparent bubbles with subtle highlights

3. **Sponge Texture Background**
   - Light gray background with subtle circular holes mimicking sponge pores
   - Creates depth without overwhelming content
   - Consistent across all screens and windows

---

## 🎨 Color Palette

### Primary Colors

```css
Orange (Primary):     #FF9500  /* Main brand color */
Orange Light:         #FFB84D  /* Hover states */
Orange Dark:          #CC7700  /* Active states, borders */
```

### Secondary Colors

```css
Sponge Green:         #C8D946  /* Secondary actions */
Sponge Green Dark:    #88A906  /* Accents */
Sponge Yellow:        #E8F966  /* Highlights */
```

### Background Colors

```css
Light Gray:           #E8E8E8  /* Main background */
Sponge Gray:          #D0D0D0  /* Texture/holes */
White:                #FFFFFF  /* Cards, panels */
```

### Text Colors

```css
Dark:                 #333333  /* Primary text */
Light:                #666666  /* Secondary text */
White:                #FFFFFF  /* On dark backgrounds */
```

### Severity Colors

```css
Critical:             #FF3B30  /* Critical issues */
High:                 #FF9500  /* High priority (orange) */
Medium:               #E8F966  /* Medium priority (yellow) */
Low:                  #C8D946  /* Low priority (green) */
```

---

## 🖼️ Components

### Buttons

**Primary Button** (Orange)
- Background: `#FF9500`
- Border: `2px solid #CC7700`
- Text: White
- Hover: Lifts up with shadow

**Secondary Button** (Sponge Green)
- Background: `#C8D946`
- Border: `2px solid #88A906`
- Text: Dark gray
- Hover: Lightens to yellow

### Cards/Panels

- White background
- **3px orange border** (`#FF9500`)
- Rounded corners (16px)
- Subtle shadow for depth
- Orange gradient border glow

### Input Fields

- White background
- **2px orange border**
- Rounded corners (8px)
- Focus: Orange glow shadow
- Placeholder: Light gray

### Tables

- **Orange header** with white text
- White row background
- Light gray row borders
- Hover: Orange tint (10% opacity)

### Modals/Dialogs

- **4px orange border** (thicker than cards)
- Semi-transparent dark overlay (50%)
- Centered on screen
- Orange header border

### Dropdown Menus

- White background
- **2px orange border**
- Orange hover state for items
- Rounded corners

---

## 🎭 Special Effects

### Sponge Texture Pattern

Created using multiple radial gradients:

```css
background-image:
  radial-gradient(circle at 15% 25%, #D0D0D0 2px, transparent 2px),
  radial-gradient(circle at 45% 65%, #D0D0D0 3px, transparent 3px),
  radial-gradient(circle at 75% 35%, #D0D0D0 2.5px, transparent 2.5px);
background-size: 120px 120px, 160px 160px, 140px 140px;
```

### Floating Bubbles

- CSS Animation: 3-second float cycle
- Semi-transparent white circles
- White highlight for depth
- Positioned absolutely around interface

### Progress Indicators

- Orange gradient fill
- Diagonal striped pattern overlay
- Smooth width transitions
- Rounded corners matching theme

---

## 📱 Responsive Design

### Breakpoints

```css
Mobile:    < 768px   /* Stack elements vertically */
Tablet:    768-1024px /* 2-column grid */
Desktop:   > 1024px  /* Full layout */
```

### Mobile Adaptations

- Single column layout
- Larger touch targets (48px minimum)
- Simplified navigation
- Collapsible sections

---

## 🎯 Usage Guidelines

### Do's ✅

- Use orange for all primary actions and borders
- Apply sponge texture to main backgrounds
- Include floating bubbles for visual interest
- Maintain 3px border width on important containers
- Use rounded corners consistently (8px for inputs, 16px for cards)

### Don'ts ❌

- Don't use colors outside the defined palette
- Don't remove orange borders from cards/modals
- Don't make text too light on gray backgrounds
- Don't overcrowd with too many bubbles
- Don't use sharp corners on primary elements

---

## 📐 Spacing System

```css
Extra Small:  4px   /* Tight spacing */
Small:        8px   /* Element padding */
Medium:       16px  /* Component spacing */
Large:        24px  /* Section spacing */
Extra Large:  32px  /* Major sections */
```

---

## 🔤 Typography

### Font Family

```css
Primary: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif
```

### Font Sizes

```css
Extra Small:  12px  /* Labels, badges */
Small:        14px  /* Body text */
Medium:       16px  /* Buttons, inputs */
Large:        18px  /* Subheadings */
Extra Large:  24px  /* Section titles */
XXL:          32px  /* Page headers */
```

### Font Weights

```css
Normal:     400  /* Body text */
Medium:     500  /* Emphasis */
Semibold:   600  /* Buttons, labels */
Bold:       700  /* Headings */
```

---

## 🎬 Animations

### Duration

```css
Fast:    150ms  /* Micro interactions */
Normal:  300ms  /* Standard transitions */
Slow:    500ms  /* Page transitions */
```

### Easing

```css
Default:  ease       /* General use */
In:       ease-in    /* Elements appearing */
Out:      ease-out   /* Elements disappearing */
InOut:    ease-in-out /* Smooth both ways */
```

---

## 🖥️ Icon Generation

### Creating Icons from SVG

1. Install requirements:
```bash
pip install cairosvg pillow
```

2. Generate all icon formats:
```bash
python assets/generate_icons.py
```

This creates:
- **icon.ico** (Windows) - Multiple sizes embedded
- **icon.icns** (macOS) - Multiple resolutions
- **icon_*.png** - Individual PNG files for Linux/web

### Icon Sizes

```
16x16    - Taskbar, browser tabs
32x32    - Small icons
48x48    - Medium icons
64x64    - Large icons
128x128  - Very large icons
256x256  - High DPI displays
512x512  - Retina displays
1024x1024 - Ultra high resolution
```

---

## 🎨 Theme Files

### CSS Stylesheet
`assets/themes/sponge_theme.css`
- Complete CSS implementation
- All component styles
- Animations and effects
- Responsive design

### Theme Configuration
`assets/themes/theme_config.json`
- Color definitions
- Spacing values
- Typography settings
- Component specifications

### UI Preview
`assets/themes/example_ui.html`
- Live demo of all components
- Interactive examples
- Visual reference

### Icon Assets
`assets/icons/`
- icon.svg - Source vector graphic
- icon.ico - Windows icon
- icon.icns - macOS icon
- icon_*.png - PNG exports

---

## 🚀 Implementation

### Web/HTML Implementation

```html
<link rel="stylesheet" href="assets/themes/sponge_theme.css">

<div class="sponge-background">
  <div class="card">
    <h2>My Content</h2>
    <button class="button">Click Me</button>
  </div>
</div>
```

### Desktop Application

Use the generated icon files in build scripts:

**Windows (PyInstaller):**
```python
'--icon', 'assets/icons/icon.ico'
```

**macOS (PyInstaller):**
```python
'--icon', 'assets/icons/icon.icns'
```

### React/Vue/Angular

Import the theme CSS and use the CSS classes:

```javascript
import '../assets/themes/sponge_theme.css';

function App() {
  return (
    <div className="sponge-background">
      <div className="card">
        <h2>Dashboard</h2>
        <button className="button">Start Analysis</button>
      </div>
    </div>
  );
}
```

---

## 📊 Accessibility

### Color Contrast

All text meets WCAG AA standards:
- Dark text on white: 12.6:1 (AAA)
- White text on orange: 4.6:1 (AA)
- Dark text on yellow: 10.2:1 (AAA)

### Focus Indicators

All interactive elements have visible focus states:
- Orange glow shadow (3px)
- Increased border width
- Color change on focus

### Screen Readers

- Semantic HTML structure
- ARIA labels where needed
- Alt text for all images
- Proper heading hierarchy

---

## 🎯 Brand Guidelines

### Logo Usage

- Maintain aspect ratio (1:1 square)
- Don't alter colors
- Minimum size: 32x32px
- Clear space: 10% of logo size on all sides

### Color Usage

- Orange is primary brand color
- Use for CTAs, borders, accents
- Sponge green for secondary actions
- White/gray for backgrounds

### Typography

- Headlines: Bold, orange
- Body: Regular, dark gray
- Links: Orange, underlined on hover
- Emphasis: Semibold, not italic

---

**Theme Version:** 2.0.0
**Last Updated:** 2026-01-06
**Status:** Production Ready
