# Parallel Development Workflow

<!--
## Usage
```bash
claude

# Initialize PRD
/project:plan <feature description>

# Iterate on PRD
/project:plan @specs/<spec>.md
```
-->

## Variables
FEATURE_OR_PLAN: $ARGUMENTS

## Do

- If FEATURE_OR_PLAN is a PRD description from the user:
    > Create a new PRD based on the provided description
- If FEATURE_OR_PLAN starts with `@specs/`:
    > Review the PRD and highlight any outstanding questions or additional context that might be needed before handing job to be done off to the dev teams

## Principles for crafting PRDs

Run through these step by step:
- First pass: Describe the problem space and the optimal solution. The file name should use the current date as a prefix.
- Second pass: Outline what the technical implementation would look like, including possible architecture design options when working with an ambiguous problem
- Third pass: Outline possible workstreams to hand off to the dev teams, highlighting concurrent workstream when possible so that we can dispatch multiple dev teams to work on different aspects of the implementation in parallel

## Resources

- PRD best practices:
    - "Inspired" by Marty Cagan - Contains practical guidance on PRDs within broader product management context
    - "The Product Manager's Handbook" by Linda Gorchels - Includes structured approaches to requirements documentation
    - "Writing Effective Use Cases" by Alistair Cockburn - While focused on use cases, many principles apply to PRDs
