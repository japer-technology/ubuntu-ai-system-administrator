# Curriculum-Gated Local AI for Children

> This is the original broad requirements study. The authoritative
> [Curriculum Flame definition](../ai-agent/curriculum-flame.md) and common
> [implementation contract](../ai-agent/implementation.md) fix the
> first-release scope, Ubuntu monorepo source root, identities, interfaces,
> data contracts, and validation order. They control wherever this study
> proposes a broader platform, service layout, repository, or feature.

## 1. Product Summary

The system is a locally hosted, general-purpose AI assistant designed for children.

A child may use the AI for broad educational and non-educational purposes, including material below or above their current school level.

The system must not teach, explain, solve, rehearse, demonstrate, or indirectly reveal curriculum outcomes that are designated as the child’s current protected learning material.

The system uses multiple independent validation layers before and after model generation. It supports warnings, session restrictions, event logging, and parent or guardian alerts.

---

## 2. Core Policy

For every curriculum learning outcome, the system assigns one of the following states:

| Curriculum state      | Access policy                   |
| --------------------- | ------------------------------- |
| Previous              | Full access                     |
| Current               | Blocked                         |
| Future                | Full access                     |
| Unclassified          | Restricted until classified     |
| Temporarily protected | Blocked for a configured period |

The primary rule is:

> Allow content below and above the learner’s current curriculum level. Block content matching the learner’s current protected curriculum outcomes.

The rule applies to direct and indirect instruction.

The system must not assume that subject year level alone is sufficient. Restrictions must be applied at the individual learning-outcome level.

---

## 3. Product Objectives

The system must:

1. Provide children with access to a capable local AI assistant.
2. Preserve access to broad knowledge and exploration.
3. Prevent the AI from replacing current classroom instruction.
4. Prevent direct assistance with protected homework and assessments.
5. Allow parents or guardians to configure and supervise access.
6. Process all prompts and responses through independent policy validators.
7. Operate without requiring prompts or child profiles to leave the local device.
8. Maintain auditable policy decisions.
9. Detect repeated attempts to bypass restrictions.
10. Provide proportionate warnings and parent alerts.

---

## 4. Non-Objectives

The first version will not:

1. Guarantee that a child cannot learn protected material elsewhere.
2. Replace teachers, schools, counsellors, or parents.
3. Infer an entire curriculum solely from the child’s age.
4. Depend on the language model to enforce policy by itself.
5. Provide unrestricted internet browsing.
6. Allow the child to change curriculum restrictions.
7. Claim perfect detection of disguised or indirect requests.
8. Automatically report every blocked prompt to a parent.
9. Store complete transcripts by default.
10. make academic assessment decisions.

---

## 5. User Roles

### 5.1 Child

The child can:

* interact with the AI
* access permitted topics
* review previous learning
* explore future learning
* use permitted non-curriculum capabilities
* view clear explanations when content is blocked
* request adult review

The child cannot:

* modify curriculum settings
* modify system policies
* disable validators
* erase protected logs
* install or replace models
* change administrator credentials
* grant the AI new tools
* disable parental alerts

### 5.2 Parent or Guardian

The parent or guardian can:

* create and manage child profiles
* assign curriculum outcomes
* mark outcomes as previous, current, or future
* configure temporary assessment protection
* view structured events
* review blocked interactions
* configure alert thresholds
* approve temporary access
* suspend access
* configure retention rules
* export reports

### 5.3 Teacher or School Administrator

Optional school-managed deployments may allow authorised staff to:

* import curriculum mappings
* publish protected learning outcomes
* define assessment protection windows
* approve exceptions
* view school-level aggregated reporting
* manage classroom policies

A teacher must not automatically receive access to private child interactions unless configured and authorised by the parent or school policy.

### 5.4 System Administrator

The system administrator can:

* install and update models
* manage devices
* configure security policies
* manage backups
* inspect system health
* review validator performance

The administrator cannot silently weaken child-protection policies without producing an audit event.

---

## 6. Functional Requirements

## 6.1 Child Profile

Each child profile must contain:

```json
{
  "learner_id": "uuid",
  "display_name": "Child",
  "date_of_birth": "YYYY-MM-DD",
  "jurisdiction": "AU-VIC",
  "school_year": 7,
  "reading_level": 7,
  "subjects": [],
  "protected_outcomes": [],
  "parent_ids": [],
  "policy_profile_id": "default-child-policy"
}
```

The system must support multiple child profiles on one device.

Each child must have an isolated conversation history, policy configuration, and event log.

---

## 6.2 Curriculum Model

The system must represent curriculum material as individual learning outcomes.

Each outcome must contain:

```json
{
  "outcome_id": "VC2M7A02",
  "framework": "Victorian Curriculum",
  "version": "2.0",
  "subject": "Mathematics",
  "strand": "Algebra",
  "title": "Solve linear equations",
  "description": "Solve one-variable linear equations using appropriate methods.",
  "year_levels": [7],
  "prerequisites": [],
  "successors": [],
  "keywords": [],
  "semantic_examples": [],
  "status": "current",
  "valid_from": "2026-08-01",
  "valid_until": "2026-09-15"
}
```

The system must support:

* jurisdiction-specific curricula
* multiple curriculum versions
* school-defined outcomes
* parent-defined outcomes
* imported curriculum packages
* outcome prerequisites
* outcome successors
* semantic relationships between outcomes
* temporary protection periods

---

## 6.3 Curriculum States

An outcome must support these states:

```text
PREVIOUS
CURRENT
FUTURE
UNCLASSIFIED
TEMPORARILY_PROTECTED
EXEMPTED
```

### PREVIOUS

The AI may:

* explain
* demonstrate
* provide worked examples
* generate exercises
* correct answers
* provide adaptive tutoring

### CURRENT

The AI must not:

* explain the learning outcome
* provide worked examples
* provide hints
* provide partial solutions
* ask leading instructional questions
* generate practice questions that teach the protected outcome
* correct attempts involving the protected outcome
* reveal the method through analogy
* provide code that performs the protected method
* translate a prohibited answer into another format

### FUTURE

The AI may provide full access unless the response would reveal a current protected outcome.

### UNCLASSIFIED

The AI must apply a configurable restricted policy.

The default behaviour is:

* provide general non-instructional information
* avoid worked examples
* request adult classification
* log the classification uncertainty

### TEMPORARILY_PROTECTED

The AI must block content for the configured period, regardless of whether the outcome would otherwise be previous or future.

### EXEMPTED

The AI may provide access under a time-limited parent or teacher authorisation.

---

## 6.4 Prompt Processing Pipeline

Every child prompt must pass through the following pipeline:

```text
Prompt received
    ↓
Authentication and profile resolution
    ↓
Prompt normalisation
    ↓
Safety classification
    ↓
Curriculum topic classification
    ↓
Learning-outcome matching
    ↓
Assessment-material matching
    ↓
Circumvention detection
    ↓
Policy decision
    ↓
Model generation
    ↓
Output safety validation
    ↓
Curriculum leakage validation
    ↓
Policy enforcement
    ↓
Response delivery
    ↓
Structured event logging
```

No prompt may be sent directly to the language model without pre-processing.

No generated response may be shown to the child without post-processing.

---

## 6.5 Prompt Normalisation

The pre-processor must:

* remove invisible characters
* detect encoded content
* detect common substitution patterns
* normalise spacing and punctuation
* detect language
* resolve references to previous conversation turns
* extract attached text
* identify quoted assignment material
* detect image-derived text where image input is enabled

The original prompt must be retained only according to configured retention policy.

---

## 6.6 Topic Classification

The topic classifier must return:

```json
{
  "subjects": [
    {
      "subject": "Mathematics",
      "confidence": 0.98
    }
  ],
  "candidate_outcomes": [
    {
      "outcome_id": "VC2M7A02",
      "confidence": 0.92,
      "relationship": "direct"
    }
  ],
  "request_type": "worked_solution",
  "instructional_intent": true,
  "classification_confidence": 0.92
}
```

Supported request types should include:

```text
GENERAL_INFORMATION
EXPLANATION
WORKED_EXAMPLE
WORKED_SOLUTION
ANSWER_CHECKING
HINT_REQUEST
PRACTICE_GENERATION
ESSAY_GENERATION
CODE_GENERATION
TRANSLATION
SUMMARISATION
ROLEPLAY
IMAGE_REQUEST
TOOL_REQUEST
UNKNOWN
```

---

## 6.7 Curriculum Matching

The matching system must use multiple methods:

1. Exact keyword matching
2. Curriculum taxonomy matching
3. Semantic embedding similarity
4. Learning-outcome classifier
5. Conversation-context analysis
6. Assessment-material similarity
7. Generated-response analysis

A single low-confidence match must not always cause a parent alert.

A high-confidence current-outcome match must block generation or force a safe response mode.

---

## 6.8 Policy Decision

The policy engine must be deterministic and separate from the language model.

It must return:

```json
{
  "decision_id": "uuid",
  "learner_id": "uuid",
  "decision": "BLOCK",
  "reason_codes": [
    "CURRENT_CURRICULUM_MATCH",
    "DIRECT_INSTRUCTION_REQUEST"
  ],
  "matched_outcomes": [
    {
      "outcome_id": "VC2M7A02",
      "confidence": 0.94
    }
  ],
  "response_mode": "CURRICULUM_REDIRECT",
  "warning_level": 1,
  "alert_level": 0,
  "allow_model_generation": false
}
```

Supported decisions:

```text
ALLOW
ALLOW_WITH_VALIDATION
REWRITE
RESTRICT
BLOCK
REQUIRE_ADULT_APPROVAL
LOCK_SESSION
```

---

## 6.9 Response Modes

The system must support these response modes:

### NORMAL

The AI provides a normal response.

### AGE_ADAPTED

The response is adjusted to the child’s reading and developmental level.

### CURRICULUM_REDIRECT

The system explains that the topic is currently protected and offers permitted alternatives.

Example:

> That topic is part of your current protected learning area, so I cannot teach or solve it here. You can review an earlier prerequisite, explore a more advanced related topic, or save the question for your teacher.

### SAFE_REWRITE

The model-generated answer is rewritten to remove protected content.

### ADULT_APPROVAL_REQUIRED

The child is informed that an adult must approve access.

### SESSION_LOCKED

Further prompts are disabled until an authorised adult reviews the session.

---

## 6.10 Post-Processing Validation

The generated response must be checked for:

* direct protected curriculum instruction
* partial protected solutions
* hidden methodological guidance
* worked examples matching protected outcomes
* answers to protected assignments
* code that solves protected work
* translated or reformatted prohibited answers
* unsafe content
* age-inappropriate content
* requests for secrecy
* manipulation
* personal-data exposure
* unauthorised external actions

The output validator must return:

```json
{
  "approved": false,
  "risk_score": 0.91,
  "violations": [
    {
      "type": "CURRENT_CURRICULUM_LEAKAGE",
      "outcome_id": "VC2M7A02",
      "confidence": 0.93
    }
  ],
  "action": "REWRITE"
}
```

---

## 6.11 Indirect Leakage Detection

The system must detect when an allowed higher-level or lower-level answer exposes current protected material.

Examples include:

* an advanced mathematics answer that teaches a protected algebraic method
* a programming example that solves a protected mathematics problem
* a historical explanation that completes a protected essay prompt
* a translation that reveals the answer to protected work
* an image containing a protected solution
* a story or analogy encoding the protected method

The post-processor must analyse the complete candidate response, not only the original prompt.

---

## 6.12 Circumvention Detection

The system should identify attempts such as:

* pretending the question is for another student
* claiming the current topic is future material
* asking for fictional or roleplayed answers
* requesting an answer in code
* requesting translation into another language
* asking for hints in multiple steps
* splitting one prohibited request across several prompts
* asking the AI to ignore policies
* encoding prompts
* using images to submit protected questions
* requesting tool execution to obtain the answer

Circumvention detection must consider recent conversation history.

---

## 6.13 Assessment Protection

Parents, guardians, or teachers must be able to protect:

* assignment text
* examination topics
* essay questions
* project briefs
* worksheets
* take-home assessments
* revision materials
* teacher-provided questions

Protected material should be represented using:

* exact hashes where appropriate
* text fingerprints
* semantic embeddings
* key phrases
* curriculum-outcome mappings

The system must detect paraphrased versions of protected material.

---

## 6.14 Warnings

Warnings must be graduated.

### Warning Level 0

No warning.

### Warning Level 1

A neutral educational boundary message.

### Warning Level 2

A stronger warning explaining that repeated attempts are recorded.

### Warning Level 3

The request is blocked and the event is marked for parent review.

### Warning Level 4

A parent alert is triggered.

### Warning Level 5

The session is suspended pending adult review.

The child must not be threatened or shamed.

---

## 6.15 Parent Alerts

Alerts may be triggered by:

* repeated protected curriculum requests
* repeated policy circumvention
* attempts to disable controls
* attempts to access administrative settings
* serious safety events
* requests involving secrecy or coercion
* attempts to contact unknown adults
* prohibited tool requests
* unusual activity patterns
* session-lock events

A parent alert should contain:

```json
{
  "event_id": "uuid",
  "timestamp": "2026-08-05T20:00:00+10:00",
  "learner_id": "uuid",
  "severity": "HIGH",
  "category": "CURRICULUM_CIRCUMVENTION",
  "subject": "Mathematics",
  "matched_outcomes": ["VC2M7A02"],
  "reason": "Repeated attempts to obtain a protected worked solution",
  "action_taken": "Response blocked",
  "attempt_count": 4,
  "requires_review": true
}
```

The system should support:

* immediate alerts
* daily summaries
* weekly summaries
* severity-based alerts
* configurable quiet hours
* in-app notifications
* local network notifications
* email notifications where configured
* mobile push notifications where configured

---

## 6.16 Parent Dashboard

The parent dashboard must provide:

* child profile management
* curriculum state management
* current protected outcomes
* temporary protection periods
* alert history
* blocked-event history
* circumvention patterns
* time spent using the AI
* permitted topic history
* learning-interest summaries
* validator confidence summaries
* temporary approval controls
* session suspension controls
* retention settings
* export controls

The dashboard should show structured summaries by default rather than full transcripts.

---

## 6.17 Temporary Access Approval

A parent or teacher may grant temporary access to a protected outcome.

Approval must include:

```json
{
  "approval_id": "uuid",
  "learner_id": "uuid",
  "outcome_ids": ["VC2M7A02"],
  "approved_by": "parent-uuid",
  "valid_from": "2026-08-05T20:00:00+10:00",
  "valid_until": "2026-08-05T20:30:00+10:00",
  "mode": "SUPERVISED",
  "reason": "Parent-assisted revision"
}
```

Approvals must expire automatically.

The child must not be able to extend an approval.

---

## 7. Safety Requirements

The system must independently classify and control:

* sexual content
* self-harm content
* suicide-related content
* violent content
* bullying
* grooming
* coercion
* requests for secrecy
* illegal activities
* dangerous instructions
* medical claims
* legal claims
* financial activity
* personal information
* communication with unknown third parties
* unauthorised purchases
* unauthorised account creation

Safety policy decisions must remain independent from curriculum decisions.

A request may be permitted by the curriculum policy but blocked by the safety policy.

---

## 8. Tool Access

The child-facing model must not receive unrestricted tool access.

Each tool must be separately authorised.

Tool categories may include:

| Tool                  | Default             |
| --------------------- | ------------------- |
| Calculator            | Allowed             |
| Local document search | Restricted          |
| Internet browsing     | Blocked             |
| Code execution        | Sandboxed           |
| File writing          | Restricted          |
| Email                 | Blocked             |
| Messaging             | Blocked             |
| Purchases             | Blocked             |
| Shell access          | Blocked             |
| Device control        | Blocked             |
| Image generation      | Age-filtered        |
| Camera access         | Permission required |
| Microphone access     | Permission required |

Tool requests must pass through the same curriculum and safety policy engine as text responses.

---

## 9. Local Deployment Requirements

The first implementation supports:

* Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`
* loopback-only child, guardian, model, and validator interfaces
* the fixed service identities in the authoritative product definition

Windows, macOS, local appliances, school networks, and mobile clients are
later portability work, not first-release requirements.

The deployment must include:

```text
Local user interface
Local API gateway
Policy engine
Curriculum database
Prompt validators
Local inference engine
Output validators
Event store
Parent dashboard
Notification service
Administrative service
```

The child-facing interface must never connect directly to the model endpoint.

---

## 10. Model Architecture

The architecture should use separate components.

```text
General-purpose language model
Curriculum classifier
Safety classifier
Circumvention classifier
Assessment matcher
Output leakage classifier
Policy engine
Alert classifier
```

A single model may implement multiple classifiers during early development, but policy decisions must remain external and deterministic.

The primary language model must not receive administrative credentials or unrestricted filesystem access.

---

## 11. Recommended Service Architecture

This tree is a conceptual decomposition, not the repository layout or a
requirement for containers, JavaScript packages, or separately deployed
microservices. The fixed Python/systemd mapping lives in the authoritative
product definition.

```text
/apps
  /child-ui
  /parent-dashboard
  /admin-console

/services
  /api-gateway
  /identity-service
  /policy-engine
  /curriculum-service
  /prompt-classifier
  /assessment-matcher
  /model-router
  /output-validator
  /alert-service
  /audit-service

/packages
  /policy-schema
  /curriculum-schema
  /event-schema
  /shared-types
  /validator-sdk

/data
  /curricula
  /policies
  /migrations

/tests
  /unit
  /integration
  /red-team
  /curriculum
  /safety
```

---

## 12. API Specification

## 12.1 Submit Child Prompt

```http
POST /v1/child/chat
```

Request:

```json
{
  "learner_id": "uuid",
  "conversation_id": "uuid",
  "message": {
    "type": "text",
    "content": "Show me how to solve this equation."
  }
}
```

Response:

```json
{
  "message_id": "uuid",
  "decision": "BLOCK",
  "response_mode": "CURRICULUM_REDIRECT",
  "content": "That topic is currently protected.",
  "warning_level": 1,
  "event_id": "uuid"
}
```

---

## 12.2 Update Curriculum Outcome

```http
PUT /v1/learners/{learner_id}/outcomes/{outcome_id}
```

Request:

```json
{
  "status": "CURRENT",
  "valid_from": "2026-08-01",
  "valid_until": "2026-09-15"
}
```

---

## 12.3 Create Temporary Protection

```http
POST /v1/learners/{learner_id}/protections
```

Request:

```json
{
  "title": "Mathematics assignment",
  "outcome_ids": ["VC2M7A02"],
  "protected_material": "attachment-reference",
  "valid_until": "2026-08-15T17:00:00+10:00"
}
```

---

## 12.4 Approve Temporary Access

```http
POST /v1/learners/{learner_id}/approvals
```

Request:

```json
{
  "outcome_ids": ["VC2M7A02"],
  "duration_minutes": 30,
  "mode": "SUPERVISED"
}
```

---

## 12.5 Retrieve Parent Events

```http
GET /v1/parents/{parent_id}/events
```

Filters:

```text
learner_id
severity
category
from
to
review_status
```

---

## 13. Data Storage

Required storage entities:

```text
Users
Learners
Parents
Guardians
Administrators
CurriculumFrameworks
CurriculumOutcomes
LearnerOutcomeStates
ProtectedMaterials
Conversations
Messages
PolicyDecisions
ValidationResults
Alerts
Approvals
Sessions
AuditEvents
SystemSettings
```

Sensitive fields must be encrypted at rest.

Administrative credentials must not be stored in the child-facing application.

---

## 14. Privacy Requirements

The default system must:

* process prompts locally
* process responses locally
* store learner profiles locally
* store curriculum mappings locally
* store event logs locally
* avoid cloud telemetry
* avoid third-party advertising
* avoid behavioural profiling
* avoid selling or sharing child data
* provide configurable retention
* allow data export
* allow authorised data deletion
* record administrative access

Cloud services must be optional and explicitly enabled.

---

## 15. Logging Requirements

The system should store structured events rather than complete transcripts by default.

Example:

```json
{
  "event_type": "POLICY_BLOCK",
  "learner_id": "uuid",
  "timestamp": "2026-08-05T20:00:00+10:00",
  "subject": "Mathematics",
  "outcome_ids": ["VC2M7A02"],
  "request_type": "WORKED_SOLUTION",
  "confidence": 0.94,
  "warning_level": 2,
  "alert_sent": false
}
```

Full transcript retention must be configurable.

Critical administrative actions must be append-only and tamper-evident.

---

## 16. Security Requirements

The system must implement:

* separate child and administrator accounts
* strong parent authentication
* encrypted local storage
* signed policy files
* signed curriculum packages
* sandboxed model execution
* sandboxed code execution
* network egress controls
* secure update verification
* rate limiting
* brute-force protection
* administrative audit logging
* session expiry
* privilege separation
* backup encryption
* policy integrity checks

The child must not be able to access the raw model endpoint.

---

## 17. Policy Integrity

The system must verify at startup that:

* curriculum policy files are signed
* validator versions are approved
* the policy engine is enabled
* the output validator is enabled
* parent controls are intact
* administrative credentials are valid
* audit logging is operational

If required safeguards are unavailable, the child-facing service must fail closed.

---

## 18. Fail-Closed Behaviour

The system must block or restrict responses when:

* the curriculum service is unavailable
* the policy engine fails
* the output validator fails
* the learner profile cannot be resolved
* the model response cannot be validated
* protected material cannot be checked
* policy files fail integrity validation
* classification confidence is below the configured threshold

The system must not silently bypass validation.

---

## 19. Performance Requirements

Target performance for a local consumer device:

| Operation                 | Target         |
| ------------------------- | -------------- |
| Prompt pre-processing     | Under 500 ms   |
| Curriculum classification | Under 1,000 ms |
| Policy decision           | Under 100 ms   |
| First model token         | Under 3,000 ms |
| Output validation         | Under 1,500 ms |
| Parent dashboard load     | Under 2,000 ms |

The system may stream internally, but response content must not be displayed before validation.

Where streaming is enabled, content must be validated in bounded chunks before display.

---

## 20. Validation Confidence Thresholds

Suggested defaults:

```text
0.90–1.00  Block when matched to current protected material
0.75–0.89  Restrict and run secondary validation
0.50–0.74  Apply conservative response mode
0.00–0.49  Treat as unclassified
```

Thresholds must be configurable by policy profile.

Safety-critical categories may use lower blocking thresholds.

---

## 21. Testing Requirements

The test suite must include:

### Unit Tests

* curriculum state transitions
* policy decisions
* alert thresholds
* approval expiry
* permission boundaries
* retention rules

### Integration Tests

* prompt-to-response pipeline
* pre-processor failure
* model failure
* output validator failure
* parent alert delivery
* curriculum import
* assessment-material matching

### Red-Team Tests

* prompt injection
* roleplay bypass
* translation bypass
* encoded prompts
* multi-turn decomposition
* image-based questions
* advanced-topic leakage
* lower-level analogy leakage
* code-generation bypass
* tool-based bypass
* administrator impersonation

### Curriculum Tests

For each protected outcome:

* direct question
* paraphrased question
* homework-style question
* worked-example request
* hint request
* answer-checking request
* advanced question containing the outcome
* lower-level question overlapping the outcome
* unrelated permitted question

---

## 22. Acceptance Criteria

The first release is acceptable when:

1. A parent can create a child profile.
2. A parent can assign curriculum outcomes as previous, current, or future.
3. Previous outcomes are available.
4. Future outcomes are available.
5. Current outcomes are blocked.
6. Direct protected questions are blocked.
7. Paraphrased protected questions are detected.
8. Generated protected content is blocked by post-processing.
9. Repeated bypass attempts produce escalating warnings.
10. Configured events produce parent alerts.
11. The child cannot modify policy settings.
12. The system operates without internet access.
13. Policy service failures cause responses to fail closed.
14. All important decisions produce structured audit events.
15. Temporary adult approvals expire automatically.

---

## 23. Minimum Viable Product

The MVP should support:

* one child profile
* one parent profile
* one curriculum jurisdiction
* one subject
* manually configured outcomes
* local model inference
* text-only interaction
* prompt classification
* deterministic policy engine
* output leakage validation
* three warning levels
* parent event dashboard
* local structured logging
* no internet access
* no external tools

Recommended first subject:

```text
Mathematics
```

Recommended first curriculum range:

```text
Years 5–8
```

Mathematics provides clearer outcome boundaries and more measurable evaluation than open-ended essay subjects.

---

## 24. Phase Two

Phase two may add:

* multiple children
* multiple parents
* school-managed profiles
* curriculum imports
* assessment document ingestion
* image input
* voice input
* additional subjects
* teacher dashboard
* mobile parent alerts
* adaptive model selection
* local learning analytics
* supervised temporary access
* local school server deployment

---

## 25. Phase Three

Phase three may add:

* curriculum knowledge graphs
* cross-subject leakage detection
* federated school policy distribution
* signed curriculum updates
* hardware appliance deployment
* policy packs by jurisdiction
* validator consensus
* explainable classification reports
* independent third-party validator plugins
* privacy-preserving aggregate reporting

---

## 26. Product-Root Deliverables

Implementation lives at `products/curriculum-flame/` in the
`japer-technology/ubuntu-zombie` repository. That product root includes:

```text
README.md
CHANGELOG.md
Makefile
PRODUCT.json
UPSTREAM.md
VERSION
docs/
payload/
scripts/manage.sh
tests/
```

Its documentation and tests include:

* sample curriculum data
* sample child policy
* sample parent policy
* test prompts
* red-team prompt suite
* API schemas
* database migrations
* local deployment instructions
* validator contract documentation

---

## 27. Fixed Source Identity

The product ID is `curriculum-flame`, its source root is
`products/curriculum-flame/`, and its release artifacts are produced from
this repository. No separate repository name remains to be selected.

---

## 28. Reference Policy

```yaml
policy:
  name: default-child-curriculum-policy
  version: 1.0

  curriculum:
    previous: allow
    current: block
    future: allow
    unclassified: restrict
    temporarily_protected: block

  current_content:
    explanations: block
    worked_examples: block
    solutions: block
    hints: block
    corrections: block
    practice_generation: block
    analogies: block
    code_solutions: block
    translation: block

  validation:
    prompt_validation: required
    output_validation: required
    conversation_validation: required
    assessment_matching: required
    fail_closed: true

  warnings:
    first_attempt: level_1
    repeated_attempts: level_2
    circumvention: level_3
    persistent_circumvention: parent_alert
    policy_tampering: session_lock

  privacy:
    local_processing: required
    cloud_telemetry: disabled
    full_transcript_storage: disabled
    structured_event_storage: enabled
```

---

## 29. Product Definition

The product should be described as:

> A locally governed, general-purpose AI environment for children that permits broad exploration while preventing the AI from teaching or solving learning outcomes currently designated as protected curriculum material.

It should not be described as:

* impossible to bypass
* guaranteed to prevent cheating
* a replacement for school instruction
* a replacement for parental supervision
* a system capable of perfectly determining educational intent

The core differentiator is the combination of:

```text
Local AI
+
Per-child curriculum mapping
+
Current-outcome exclusion
+
Independent pre-processing
+
Independent post-processing
+
Warnings and escalation
+
Parent-controlled alerts
```
