# Product Specification

## Goal

Find the correct engineering file quickly by part number/code and inspect it without opening heavyweight desktop tools.

## Search principles

- forgiving about formatting, conservative about identity
- deterministic and reproducible ranking
- exact matches always outrank fuzzy candidates
- fuzzy candidates are suggestions, never automatic replacements
- user input order is preserved
- normal search reads SQLite only; filesystem scanning is explicit/startup work
- every recommended result explains why it matched

## In scope

- batch code search
- All-formats search or format-specific search
- case/separator/extension normalization
- explicit revision detection
- deterministic match ranking
- released/current/supplier/WIP/archive folder priority
- strong-match alternatives
- conservative fuzzy suggestions
- result filters: All, Found, Multiple, Suggested, Missing
- index status and manual refresh
- optional working-folder scope
- configured default roots
- preview grid
- interactive STEP previews
- large preview modal
- source download
- STEP/STP, PDF, DXF, Word, Excel, PowerPoint, Markdown, Text, and HTML

## Out of scope

- login / user accounts / permissions
- LDAP / API keys
- admin console or dashboard
- semantic/LLM search
- OCR or document full-text search
- ERP/PLM integration
- automatic fuzzy substitution
- authoritative CAD/B-rep validation

## STEP limitation

STEP preview geometry is tessellated and intended for quick inspection. Exact B-rep/topology validation belongs in CAD software.
