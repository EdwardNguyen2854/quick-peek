# Product Specification

## Goal

Find engineering files quickly by code and inspect them without opening heavyweight desktop tools.

## In scope

- batch code search
- optional working-folder selection
- configured default roots
- preview grid
- large preview modal
- source download
- STEP/STP, PDF, DXF, and supported document formats
- tessellated STEP 3D viewing when a STEP → GLB converter is configured

## Out of scope

- login
- user accounts
- roles / permissions
- LDAP / API keys
- admin console
- dashboard / usage analytics
- roadmap / releases / info pages

## STEP limitation

STEP preview geometry is tessellated and intended for quick inspection. Exact B-rep/topology validation belongs in CAD software.
