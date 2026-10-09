# TOM-01 Instruction Authoring Guidelines

This document describes a generic Markdown template and guidance for creating TOM-style instructions (e.g., `TOM_01`) used by automation and test generation tools. Do not include concrete, hardcoded step-by-step actions — instead provide placeholders and structured fields that authors should fill in when creating TOM definitions.

## Purpose
- Explain the intent of the TOM (what area, feature, or user journey it covers).
- Provide a structured, reusable format so other TOMs can be created consistently.

## Recommended Structure (Template)
Use the following headings and bullet fields. Keep each field concise and avoid hardcoding specific interactions.

### TOM Metadata
- **TOM_NUM:** (e.g., `TOM_01`)
- **Title / User Journey:** Short descriptive title of the journey or feature.
- **Description:** One-paragraph summary explaining the goal and scope.
- **Priority:** (Optional) High / Medium / Low
- **Tags:** (Optional) comma-separated list of relevant tags (e.g., mobile, plp, quote)

### Preconditions
- **Account state:** Describe required user/account preconditions (e.g., logged in, specific role).
- **Data prerequisites:** Describe required data or environment setup (e.g., product catalog available, test user exists).
- **Assumptions:** Any assumptions about UI, network, or backend behavior.

### High-level Flow
Provide a concise, numbered list of high-level tasks or checkpoints the TOM should validate. These are checkpoints only — not implementation steps or selectors. Examples of checkpoint phrasing:
- Verify page shell and main tabs are visible.
- Validate that a quote can be created and contains expected header fields.
- Confirm address lookup returns suggestions for a valid input.

### Input Fields (Placeholders)
List the inputs that test authors or automation builders should supply. Use descriptive names rather than hardcoded values.
- `USERNAME` — placeholder for login username
- `PASSWORD` — placeholder for login password
- `SEARCH_TERM` — placeholder for product or feature search
- `CONTACT_PHONE` — placeholder for contact phone number
- `EMAIL_ADDRESS` — placeholder for contact email
- `ADDRESS_LOOKUP_INPUT` — placeholder for the free-text address search

### Verification/Assertions
Describe the kinds of verifications to perform, without giving exact selectors or test steps. Use general assertions such as:
- Page title equals expected value.
- Customer name appears in quote header.
- Coverage summary includes expected network capabilities.
- Cart updates after adding an item.
- Payment and review pages can be navigated to and confirm order submission state.

### Post-conditions / Cleanup
- Describe required cleanup steps to leave the environment in a reusable state (e.g., delete test quote, deallocate reserved stock).

### Example (Abstract)
> TOM_NUM: TOM_XX
>
> Title: Example user journey
>
> Description: Validate that the user can perform the journey and the system records expected summary data.
>
> Preconditions: test user exists, product catalog loaded
>
> Inputs: `USERNAME`, `PASSWORD`, `SEARCH_TERM`, `CONTACT_PHONE`
>
> Checkpoints:
>- Page shell visible
>- Product selected and added to cart
>- Quote created with customer name
>- Order submitted and order number generated

## Style & Best Practices
- Use placeholders not concrete values — avoid specific usernames, phone numbers, IMEIs, or IDs.
- Keep steps high-level and assertion-focused.
- Use consistent field names across TOMs for automation compatibility.
- Prefer descriptive text over UI implementation details.
- Add tags and priority to make filtering easier for generation tools.

## Where to store
- Place TOM authoring files under `.github/agents/` with a clear filename matching the TOM number or purpose.

## Minimal Template to Copy
```
# TOM Metadata
- TOM_NUM: TOM_XX
- Title / User Journey: 
- Description: 
- Priority: 
- Tags: 

# Preconditions
- Account state: 
- Data prerequisites: 
- Assumptions: 

# High-level Flow
1. 
2. 
3. 

# Input Fields
- USERNAME:
- PASSWORD:
- SEARCH_TERM:
- CONTACT_PHONE:
- EMAIL_ADDRESS:
- ADDRESS_LOOKUP_INPUT:

# Verification/Assertions
- 
- 

# Post-conditions / Cleanup
- 
```

---

If you want, I can convert an existing TOM JSON file into this Markdown template, leaving placeholders where the original contained concrete values. Let me know which file to convert.