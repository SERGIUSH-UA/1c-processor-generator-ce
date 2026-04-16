# Sync Tool Development Roadmap

**Version:** 2.42.0+
**Status:** In Development
**Last Updated:** 2025-11-26

## Vision

Створити найзручніший інструмент для bidirectional синхронізації між YAML+BSL (source of truth) та EPF/XML (1C Configurator edits), який дозволяє:
- Швидко вносити мінорні правки в Конфігураторі без повної регенерації
- LLM агентам автоматично синхронізувати зміни
- Зберігати single source of truth в YAML+BSL
- Підтримувати ітеративний розробницький workflow

---

## Phase 1: MVP (v2.25.0) ✅ COMPLETED

**Status:** ✅ Delivered
**Completion Date:** 2025-01-19

### Deliverables

✅ **Core Modules:**
- `xml_differ.py` - XML comparison engine
- `bsl_differ.py` - BSL code comparison
- `change_mapper.py` - Change mapping to YAML/BSL updates
- `sync_tool.py` - CLI interface with LLM mode

✅ **Generator Integration:**
- Automatic snapshot creation during generation
- Snapshot structure: `_snapshot/original.xml`, `original_handlers.bsl`, `metadata.json`

✅ **CLI Command:**
- `python -m 1c_processor_generator sync` subcommand
- Interactive mode (preview + confirmation)
- LLM mode (--llm-mode) with JSON output

✅ **Supported Changes:**
- Attribute/Element **rename**
- Property changes (title, tooltip, width)
- BSL procedure modifications
- Type changes

### Known Limitations

⚠️ **Not Supported in MVP:**
- Adding/deleting elements (structural changes)
- Form XML files (separate from processor)
- TabularSection column add/delete
- Multi-form processors (only first form synced)
- Conflict resolution (manual merge required)

---

## Phase 2: Core Improvements (v2.26.0 - v2.28.0)

**Target:** Q1-Q2 2025
**Focus:** Robustness, coverage, UX improvements

### 2.1 Structural Changes Support (v2.26.0)

**Priority:** HIGH
**Effort:** 2-3 weeks

**Features:**
- ✨ Add/delete attributes
- ✨ Add/delete form elements
- ✨ Add/delete TabularSection columns
- ✨ Smart conflict detection (e.g., delete in XML but still referenced in BSL)

**Success Criteria:**
- Can add new InputField in Configurator → auto-updates YAML
- Can delete attribute → shows warning if referenced in BSL
- Integration tests cover 20+ structural change scenarios

**Technical Approach:**
- Extend `_compare_elements()` to handle structural diffs
- Add `YAMLPatcher` class for safe YAML insertion/deletion
- Implement reference checker (find BSL references to deleted elements)

---

### 2.2 Multi-Form Support (v2.26.1)

**Priority:** MEDIUM
**Effort:** 1 week

**Features:**
- ✨ Sync all forms in multi-form processors (not just first)
- ✨ Form-specific snapshots
- ✨ Selective sync (`--form=Форма`)

**Success Criteria:**
- Processor with 3 forms → sync correctly detects changes in each
- Can sync only specific form without affecting others

**Technical Approach:**
- Store per-form snapshots in `_snapshot/forms/Форма/`
- Extend `_save_snapshot()` to iterate all forms
- Add form filtering in sync_tool

---

### 2.3 Separate Form XML Support (v2.27.0)

**Priority:** HIGH
**Effort:** 2 weeks

**Features:**
- ✨ Detect changes in separate `Форма.xml` files
- ✨ Form module BSL sync
- ✨ Form metadata (AutoCommandBar, events)

**Success Criteria:**
- Sync works with both embedded and separate form XMLs
- Form module changes (OnOpen, commands) correctly synced

**Technical Approach:**
- Extend `XMLDiffer` to handle form XML structure
- Parse form events and map to YAML `form.events`
- Handle form-specific BSL (Module.bsl vs FormModule.bsl)

---

### 2.4 Smart Merge & Conflict Resolution (v2.28.0)

**Priority:** HIGH
**Effort:** 3 weeks

**Features:**
- ✨ Three-way merge (original, YAML changes, XML changes)
- ✨ Conflict detection (both sides changed same element)
- ✨ Interactive conflict resolution UI
- ✨ Merge strategies (keep YAML, keep XML, manual)

**Example Conflict:**
```yaml
# YAML changed:
attributes:
  - name: Product
    title: "New Title from YAML"

# XML changed:
<Title>Different Title from Configurator</Title>

# Conflict: Both changed title → ask user
```

**Success Criteria:**
- Detects conflicts with 95%+ accuracy
- Offers clear conflict resolution choices
- Can auto-resolve non-conflicting changes

**Technical Approach:**
- Add `ConflictDetector` class
- Three-way diff algorithm
- Interactive TUI using `rich` library for conflicts

---

## Phase 3: Advanced Features (v2.29.0 - v2.32.0)

**Target:** Q3 2025
**Focus:** Automation, intelligence, developer experience

### 3.1 Watch Mode (v2.29.0)

**Priority:** HIGH
**Effort:** 1-2 weeks

**Features:**
- ✨ `--watch` flag for continuous monitoring
- ✨ Auto-sync when XML file changes
- ✨ Desktop notification on sync completion
- ✨ File system watcher (inotify/watchdog)

**Use Case:**
```bash
# Terminal 1: Watch mode running
python -m 1c_processor_generator sync --watch \
  --modified-xml tmp/MyProcessor/MyProcessor.xml \
  --config config.yaml \
  --handlers handlers.bsl \
  --auto-apply

# Terminal 2: User edits in Configurator, saves XML
# → Watch mode detects change
# → Auto-syncs to YAML+BSL
# → Shows notification "✅ Synced 3 changes"
```

**Success Criteria:**
- Detects file changes within 1 second
- Stable over 8+ hour work session
- Low CPU usage (<1% idle)

**Technical Approach:**
- Use `watchdog` library for file monitoring
- Debounce rapid changes (wait 2s after last change)
- Optional desktop notifications (`plyer` library)

---

### 3.2 Incremental YAML Updates (v2.30.0) ✅ COMPLETED

**Status:** ✅ COMPLETED (2025-11-20)
**Priority:** MEDIUM
**Effort:** 2 weeks (Actual: 1 week)

**Features:**
- ✅ Preserve YAML comments
- ✅ Preserve YAML ordering
- ✅ Preserve YAML formatting (indentation, spacing)
- ✅ Minimal diff (change only what's needed)

**Current Issue:** ✅ RESOLVED
```yaml
# Before sync (with comments):
attributes:
  # This is user's important comment
  - name: Product
    type: string

# After sync (comments preserved!):
attributes:
  # This is user's important comment
  - name: Product
    type: number  # Type changed, comment preserved!
```

**Success Criteria:** ✅ ALL MET
- ✅ 100% comment preservation (4/4 comments preserved in manual test)
- ✅ 100% formatting preservation (indentation, spacing, ordering)
- ✅ YAML diff shows only semantic changes

**Implementation:**
- ✅ Created `yaml_comment_utils.py` (135 lines, 3 helper functions)
- ✅ Enhanced `ruamel.yaml` configuration (4 files)
- ✅ Refactored 16 methods to preserve comments
- ✅ 29 new unit tests (100% passing)
- ✅ Zero regressions (308/308 tests pass)
- ✅ Round-trip test validates comment preservation

**Technical Approach:**
- Enhanced `ruamel.yaml` configuration (map_indent, sequence_indent, sequence_dash_offset)
- Custom YAML updater preserving comments (`update_value_preserving_comments()`)
- Round-trip test (sync → parse → compare) ✅ PASSED

---

### 3.3 AI-Assisted Change Explanation (v2.31.0)

**Priority:** LOW
**Effort:** 1 week

**Features:**
- ✨ Auto-generate human-readable change summary
- ✨ Detect change patterns (e.g., "Renamed for consistency")
- ✨ Suggest commit messages based on changes

**Example Output:**
```
📊 Sync Summary:

Detected 5 changes:
• Renamed 'Tovar' → 'Product' (consistency with English naming)
• Changed Product type: string → number (data model alignment)
• Modified CalculateTotal procedure (fixed calculation bug)
• Added new field 'Discount' (pricing feature)

Suggested commit message:
"refactor: rename Tovar to Product and fix CalculateTotal"
```

**Success Criteria:**
- Generates meaningful summaries for 80%+ of changes
- Commit messages follow conventional commits spec

**Technical Approach:**
- Pattern matching on change types
- Heuristics for change categorization
- Optional LLM integration (local/remote)

---

### 3.4 Partial Sync (v2.32.0)

**Priority:** MEDIUM
**Effort:** 1 week

**Features:**
- ✨ Sync only specific sections (`--only attributes`)
- ✨ Exclude sections (`--exclude bsl`)
- ✨ Element-level granularity (`--only attributes.Product`)

**Use Cases:**
```bash
# Only sync BSL changes, ignore XML
sync --modified-xml modified.xml --config config.yaml --only bsl

# Only sync specific attribute
sync --modified-xml modified.xml --config config.yaml --only attributes.Product

# Sync everything except commands
sync --modified-xml modified.xml --config config.yaml --exclude commands
```

**Success Criteria:**
- Can selectively sync with 100% accuracy
- Clear error messages for invalid selectors

**Technical Approach:**
- Add filtering in `ChangeMapper.map_xml_changes()`
- JSONPath-like selector syntax
- Validation of selectors against YAML structure

---

## Phase 4: Enterprise & Production (v2.33.0+)

**Target:** Q4 2025 and beyond
**Focus:** Team workflows, CI/CD, advanced automation

### 4.1 Team Collaboration (v2.33.0)

**Priority:** MEDIUM
**Effort:** 3 weeks

**Features:**
- ✨ Git integration (auto-commit after sync)
- ✨ Branch-aware sync (different snapshots per branch)
- ✨ Team settings (shared sync policies)
- ✨ Change history and audit log

**Use Case:**
```bash
# Team settings in .sync.yaml
team:
  auto_commit: true
  commit_template: "sync: {summary}"
  require_approval: false
  snapshot_per_branch: true

# After sync:
# → Creates commit with standardized message
# → Pushes to current branch
# → Notifies team via webhook
```

**Success Criteria:**
- Seamless git integration
- No merge conflicts from sync operations
- Clear audit trail of all syncs

---

### 4.2 CI/CD Integration (v2.34.0)

**Priority:** HIGH
**Effort:** 2 weeks

**Features:**
- ✨ `sync validate` command (check if YAML/XML in sync)
- ✨ Exit codes for CI (0=synced, 1=out of sync, 2=conflicts)
- ✨ GitHub Actions workflow examples
- ✨ Pre-commit hooks

**Example CI Workflow:**
```yaml
# .github/workflows/sync-check.yml
name: Sync Check
on: [pull_request]
jobs:
  check:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check sync status
        run: |
          python -m 1c_processor_generator sync validate \
            --config config.yaml \
            --handlers handlers.bsl \
            --fail-if-out-of-sync
```

**Success Criteria:**
- CI/CD integration examples for 3+ platforms (GitHub, GitLab, Jenkins)
- Pre-commit hook prevents commits when out of sync

---

### 4.3 Advanced Validation (v2.35.0)

**Priority:** MEDIUM
**Effort:** 2 weeks

**Features:**
- ✨ Semantic validation (changes don't break references)
- ✨ Business rule validation (custom validators)
- ✨ Performance impact analysis (large change warnings)
- ✨ Dependency checking (attribute used in BSL)

**Example Validation:**
```bash
sync --modified-xml modified.xml --config config.yaml --validate-strict

⚠️  Validation Warnings:
• Attribute 'Tovar' renamed to 'Product'
  → Found 12 references in BSL code
  → Will auto-update references

❌ Validation Errors:
• Deleted attribute 'Price' is required by:
  → CalculateTotal procedure (line 45)
  → ValidateData procedure (line 78)
  → Cannot sync until references removed
```

**Success Criteria:**
- Catches 95%+ of breaking changes before sync
- Actionable error messages with fix suggestions

---

### 4.4 GUI Tool (v2.36.0)

**Priority:** LOW
**Effort:** 4-6 weeks

**Features:**
- ✨ Standalone GUI application (Electron or Qt)
- ✨ Visual diff viewer (side-by-side XML/YAML)
- ✨ Drag-and-drop file selection
- ✨ One-click sync with preview
- ✨ Settings management UI

**Success Criteria:**
- Non-technical users can sync without CLI
- Cross-platform (Windows, macOS, Linux)
- Intuitive UX (< 5 clicks to sync)

---

## Phase 5: Intelligence & Automation (Future)

**Target:** 2026+
**Focus:** AI-powered features, predictive capabilities

### 5.1 Smart Recommendations

**Features:**
- AI suggests optimal sync strategy based on changes
- Auto-categorize changes (bug fix, feature, refactor)
- Predict potential issues before sync
- Learn from user's past sync decisions

---

### 5.2 Reverse Engineering

**Features:**
- Full EPF → YAML+BSL conversion (not just sync)
- Import existing processors into generator format
- Migrate legacy processors to new architecture

---

### 5.3 Cloud Sync

**Features:**
- Cloud-based snapshot storage
- Team sync via cloud service
- Real-time collaboration (multiple devs)
- Version history and rollback

---

## Success Metrics

### MVP (Phase 1)
- ✅ 5+ change types supported
- ✅ LLM-friendly JSON output
- ✅ 0 data loss (via backup)

### Phase 2 Targets
- 90% test coverage for sync modules
- Sync 20+ structural change types
- <100ms diff calculation time
- <1s sync application time

### Phase 3 Targets
- Watch mode stability: 99.9% uptime over 8h
- 100% YAML formatting preservation
- User satisfaction: 4.5+/5 stars

### Phase 4 Targets
- 3+ CI/CD platform integrations
- 95%+ breaking change detection
- Team adoption: 10+ teams using sync in production

---

## Contributing

Хочете допомогти з розвитком sync tool? Ось як:

1. **Pick a feature** - Виберіть feature з roadmap
2. **Open issue** - Створіть GitHub issue з описом implementation plan
3. **Submit PR** - Надішліть pull request з implementation
4. **Add tests** - Додайте integration tests (мінімум 80% coverage)
5. **Update docs** - Оновіть документацію

**Priority Features for Contributors:**
- 🔥 Structural changes support (v2.26.0)
- 🔥 Multi-form support (v2.26.1)
- 🔥 Watch mode (v2.29.0)
- ⭐ Incremental YAML updates (v2.30.0)

---

## Changelog

**v2.42.0** (2025-11-26) - Handler Architecture & New Element Types
- ✅ **Handler Registry Pattern** - Extensible handler architecture (`sync/` package)
- ✅ **9 Element Handlers:** attribute, form_element, command, tabular_section, value_table, form_attribute, form, template, form_parameter
- ✅ **Template Sync** - HTMLDocument, SpreadsheetDocument support
- ✅ **FormParameter Sync** - Form parameters with key_parameter, synonym
- ✅ **Full Property Mapping:**
  - font (bold, italic, size, face_name)
  - horizontal_align, vertical_align
  - choice_mode, quick_choice, choice_history_on_input
  - multiline, password_mode, text_edit
  - picture, picture_size, zoomable
  - group_direction, representation, show_title
- ✅ **38 new handler tests** (100% passing)

**v2.30.0** (2025-11-20) - Comment & Formatting Preservation
- ✅ Full comment preservation during sync
- ✅ YAML formatting preservation

**v2.26.0** (2025-11-19) - Structural Changes
- ✅ Add/delete attributes, form elements, commands
- ✅ YAMLPatcher for safe YAML modifications
- ✅ Reference checker

**v2.25.0** (2025-01-19)
- ✅ Initial sync tool implementation
- ✅ XML/BSL differ modules
- ✅ LLM-friendly mode
- ✅ Snapshot generation

---

## Questions & Feedback

**Contact:** GitHub Issues
**Documentation:** [docs/SYNC_GUIDE.md](./SYNC_GUIDE.md) (coming soon)
**Examples:** [examples/sync/](../examples/sync/) (coming soon)

---

**Last Updated:** 2025-01-19
**Maintained by:** 1C Processor Generator Team
