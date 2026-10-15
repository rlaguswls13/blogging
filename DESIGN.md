# AI Blogging Theme Design Contract

## Purpose

The Blogger theme presents technical articles with a quiet editorial layout. New elements preserve the existing visual language and reuse the theme's CSS variables.

## Tokens

- Color: `--primary-color`, `--primary-light`, `--text-main`, `--text-muted`, `--card-bg`, `--border-color`
- Typography: `--font-family`; body copy uses the existing `1.05rem` article scale and supporting copy uses `0.9rem`
- Radius: article surfaces use `12px`; supporting surfaces use `10px`
- Spacing: values follow the existing 4px-based spacing rhythm

## Components

- `post-detail`: primary article surface
- `post-meta`: publication metadata and the editorial author link
- `editorial-disclosure`: compact disclosure of the automated drafting, validation, and administrator approval process

## Accessibility

- Author and policy destinations are real links.
- The editorial disclosure has an accessible label and remains readable without color.
- Existing responsive layout and focus behavior must remain intact.

## Accepted constraints

- Blogger Layouts V3 controls the runtime data model and final serialization.
- The theme uses one inline stylesheet and Blogger XML widgets rather than a component build system.
