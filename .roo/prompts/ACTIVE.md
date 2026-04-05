# Prompt: Comprehensive Code Review and Report Generation
Generated: 2026-04-03T11:55:00Z
Task Type: documentation

---

## Context

### Project Overview
BitbotV7 is a Bitcoin trading bot with a Flask web UI and REST API. The bot runs on a Raspberry Pi 3B and supports three trading styles (scalping, day trading, swing trading) across three modes (paper, testnet, live).

### Background
Roo has completed an initial architectural review identifying several issues:
- Silent early returns causing UI to appear frozen
- Potential race conditions in position management
- Missing error handling for API failures
- Performance bottlenecks from repeated kline fetches
- Threading/synchronization concerns

A preliminary report was generated but needs validation and expansion through actual code analysis.

### Files Already Reviewed by Roo:
- [`src/main.py`](src/main.py) — Entry point
- [`src/bot/bot_runner.py`](src/bot/bot_runner.py) — Main bot loop (353 lines)
- [`src/bot/strategy/signal_generator.py`](src/bot/strategy/signal_generator.py) — Signal generation
- [`src/bot/execution/binance_client.py`](src/bot/execution/binance_client.py) — API client
- [`src/bot/risk/risk_manager.py`](src/bot/risk/risk_manager.py) — Risk management
- [`src/bot/analysis/session_analyzer.py`](src/bot/analysis/session_analyzer.py) — Session detection
- [`src/ui/templates/index.html`](src/ui/templates/index.html) — UI template (1102 lines)
- [`src/data/models/position.py`](src/data/models/position.py) — Position model
- [`src/ui/app.py`](src/ui/app.py) — Flask app factory
- [`src/api/routes/activity_routes.py`](src/api/routes/activity_routes.py) — Activity endpoints

---

## Task

Conduct a comprehensive code review of the entire BitbotV7 codebase and generate a detailed report covering:

1. **Code Quality Assessment** — Style, structure, maintainability
2. **Error Analysis** — Identify actual bugs, potential issues, edge cases
3. **Performance Review** — Profile hot paths, identify bottlenecks
4. **Security Audit** — Check for vulnerabilities, proper input validation
5. **Architecture Evaluation** — Assess design decisions, coupling, cohesion
6. **Testing Coverage** — Evaluate test completeness (or lack thereof)
7. **Documentation Review** — Check docstrings, comments, CLAUDE.md accuracy
8. **Recommendations** — Prioritized list of improvements with rationale

---

## Requirements

### Scope
**Include:**
- All Python source files in `src/`
- UI templates and embedded JavaScript
- Configuration files (settings, presets)
- Data models and storage layer
- API routes and schemas

**Exclude:**
- Generated/cache files
- Virtual environment contents
- Log files and data directories

### Review Methodology
1. **Static Analysis** — Read all source files systematically
2. **Cross-Reference Validation** — Verify Roo's preliminary findings against actual code
3. **Deep Dive Analysis** — Examine complex logic paths, edge cases
4. **Pattern Recognition** — Identify anti-patterns, code smells
5. **Best Practices Check** — Compare against Python/Flask/trading bot standards

### Report Structure
Generate a markdown report to `.roo/results/code-review-report.md` with:

```
# BitbotV7 Code Review Report
Generated: [timestamp]
Reviewer: Claude Code

## Executive Summary
[2-3 paragraph overview of code quality, major findings, overall assessment]

## 1. Architecture Assessment
### Structure and Organization
[Analysis of module separation, dependencies, coupling]

### Design Patterns
[Patterns used effectively or missing]

### Thread Safety Analysis
[Detailed threading review with specific examples]

## 2. Code Quality Metrics
| Metric | Status | Notes |
|--------|--------|-------|
| Type Coverage | [assessment] | [details] |
| Docstring Coverage | [assessment] | [details] |
| Function Length | [assessment] | [details] |
| Cyclomatic Complexity | [assessment] | [details] |

## 3. Error Analysis
### Critical Issues
[Issues that could cause data loss, incorrect trades, or crashes]

### High Priority Issues
[Significant bugs or design flaws]

### Medium Priority Issues
[Code quality problems, missing features]

### Low Priority Issues
[Nitpicks, style inconsistencies]

## 4. Performance Analysis
### Hot Path Identification
[Functions called frequently with high cost]

### Bottleneck Analysis
[I/O bottlenecks, CPU-intensive operations]

### Recommendations
[Specific optimizations with estimated impact]

## 5. Security Assessment
### Vulnerabilities Found
[Any security issues identified]

### Best Practices Compliance
[Input validation, authentication, etc.]

## 6. Testing Assessment
### Current State
[Test coverage analysis]

### Gaps Identified
[Untested critical paths]

### Recommendations
[Prioritized testing strategy]

## 7. File-by-File Review
### [filename] — [brief description]
**Lines:** X | **Complexity:** [low/medium/high] | **Issues:** N

[Detailed review of each significant file]

## 8. Recommendations Summary
### Immediate (Fix Before Next Trade)
1. [Issue] — [Rationale] — [Effort: S/M/L]

### Short-term (Next Sprint)
1. [Issue] — [Rationale] — [Effort: S/M/L]

### Long-term (Architecture Improvements)
1. [Issue] — [Rationale] — [Effort: S/M/L]

## 9. Code Snippets Requiring Attention
[Specific line numbers and code blocks that need fixes]

## Appendix A: Files Reviewed
[List of all files examined with line counts]

## Appendix B: Questions for Developer
[Any clarifications needed]
```

### Coding Standards Compliance
- Follow `.roo/rules/01-coding-standards.md` for any code examples in report
- Reference specific line numbers for all issues found
- Use clickable links to source files where applicable

---

## Code References

### Key Files to Focus On:
| File | Lines | Primary Concern |
|------|-------|----------------|
| [`src/bot/bot_runner.py`](src/bot/bot_runner.py) | 353 | Threading, silent failures |
| [`src/bot/strategy/signal_generator.py`](src/bot/strategy/signal_generator.py) | 173 | Signal logic correctness |
| [`src/bot/execution/binance_client.py`](src/bot/execution/binance_client.py) | 107 | Error handling, retries |
| [`src/ui/templates/index.html`](src/ui/templates/index.html) | 1102 | JavaScript bugs, XSS |

### Roo's Preliminary Findings to Validate:
1. Silent early returns at lines 214-225 in bot_runner.py
2. Race condition potential at lines 174-177 in bot_runner.py
3. Missing error logging for price fetch failures at lines 158-162
4. Hardcoded "1m" timeframe at line 227
5. No retry logic in binance_client.py
6. Inefficient kline fetching every tick

---

## Success Criteria

- [ ] All Python files in `src/` reviewed systematically
- [ ] Each issue includes specific file path and line number
- [ ] Issues categorized by severity (Critical/High/Medium/Low)
- [ ] Performance analysis includes estimated costs and recommendations
- [ ] Threading analysis covers all shared state access points
- [ ] Security review addresses API endpoints, input validation, authentication
- [ ] Recommendations are actionable with effort estimates (S/M/L)
- [ ] Report is comprehensive but readable (under 10,000 words)
- [ ] Code examples in report follow project coding standards
- [ ] All of Roo's preliminary findings validated or refuted with evidence

---

## Notes

- This is a **read-only** task — do not modify any source files
- Focus on analysis and documentation, not implementation
- Be thorough but pragmatic — distinguish between theoretical issues and real problems
- Consider the trading context — some "issues" may be intentional design decisions
- Cross-reference with CLAUDE.md to verify documented behavior matches implementation
