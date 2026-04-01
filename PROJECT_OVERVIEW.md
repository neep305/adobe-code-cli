# Adobe Experience Platform AI Agent (AEP Agent)

**대화형 인터페이스를 통한 AEP 운영 자동화 에이전트**

기존의 복잡한 CLI 커맨드 입력 방식에서 벗어나, AI 에이전트와의 자연어 대화 및 가이드된 워크플로우를 통해 AEP 설정을 자동화합니다. 사용자가 커맨드를 외울 필요 없이, 에이전트가 단계를 리드하며 실행 결과를 보고합니다.

---

## 🎯 Project Overview

### What It Does
사용자의 의도를 분석하여 복잡한 API 호출 체인을 에이전트가 대신 실행합니다.

```bash
# 사용자는 단순히 에이전트를 실행하거나 특정 파일을 지정합니다.
aep assistant --file sales.csv

# 에이전트가 메뉴를 제시합니다:
# ? 어떤 작업을 진행할까요?
# > [1] 데이터 분석 및 스키마 생성 플랜 수립
#   [2] 기존 데이터셋에 업로드 (Batch Ingestion)
#   [3] 데이터 품질 검사 및 리포트 생성
#   [4] 기타 자유 질의 (Chat Mode)

# 선택 후: 에이전트가 해당 '플랜'을 시각적으로 보여주고 승인을 요청합니다.
```

**Core Value**: "Claude Code for Adobe Services" - AI makes decisions at every step, not just API calls.

---

## ⚡ Key Features

### 1. AI-Powered Schema Management
- **Automatic XDM Schema Generation**
  - Analyze CSV/JSON sample data
  - Generate AEP-compliant schemas
  - Suggest identity namespaces
  - Validate against XDM standards
- **Entity Relationship Diagrams (ERDs)**
  - Auto-detect data relationships
  - Visual schema documentation
- **Schema Optimization**
  - AI suggests field types, constraints
  - Identifies missing required fields

### 2. Intelligent Data Ingestion
- **Batch Upload Automation**
  - CSV, JSON, Parquet support
  - Auto-detect data format
  - Pre-validate before upload
- **Data Quality Checks**
  - AI infers validation rules
  - Type checking and null handling
  - Duplicate detection
- **Identity Resolution**
  - AI recommends identity fields
  - Namespace mapping automation

### 3. Natural Language Interface
- **Conversational CLI**
  - "Create schema for customer events with email as primary ID"
  - AI interprets intent, suggests actions
- **Context-Aware Help**
  - Error explanations in plain English
  - Suggest fixes for common issues
- **Onboarding Assistant**
  - Interactive setup wizard
  - Q&A during configuration

### 4. Technical Documentation
- **Auto-Generated Specs**
  - Field-level descriptions
  - Schema versioning history
  - Data lineage diagrams
- **API Documentation**
  - Automatically track schema changes
  - Generate migration guides

---

## 🎯 Goals & KPIs

### Primary Goal
**Reduce hands-on engineering resources by 80-85%** for AEP integration projects

### Key Performance Indicators

| Metric | Baseline (Manual) | Target (AI-Assisted) | Improvement |
|--------|-------------------|----------------------|-------------|
| **Schema Creation** | 2-4 hours | 5-10 minutes | **90% faster** |
| **Data Ingestion Setup** | 4-8 hours | 15-30 minutes | **85% faster** |
| **Technical Docs** | 3-5 hours | 10-20 minutes | **90% faster** |
| **Developer Hours/Project** | 10-15 hours | 2-3 hours | **80% reduction** |
| **Annual Cost Savings** | - | **$24K+** | (20 projects/year) |

### Success Metrics
- ✅ **XDM Validation Pass Rate**: >95% on first attempt
- ✅ **Data Mapping Accuracy**: >98% correct field mappings
- ✅ **Developer Satisfaction**: >4.5/5
- ✅ **Self-Service Adoption**: >60% of projects without architect support

---

## 🛤️ Development Roadmap

### Phase 1: Foundation (Current → Q2 2026)
**Focus**: Schema Management & Core Infrastructure

#### Milestones
1. **Schema Generation Engine** ✅ *In Progress*
   - AI-powered XDM schema creation
   - Sample data analysis (CSV, JSON)
   - XDM validation and compliance checks
   - **Delivery**: March 2026

2. **AEP API Integration** 🔄 *Next*
   - OAuth authentication flow
   - Catalog Service (dataset operations)
   - Schema Registry (XDM schema CRUD)
   - **Delivery**: April 2026

3. **CLI Framework** 📋 *Planned*
   - Typer-based command structure
   - Rich terminal UI (tables, progress bars)
   - Configuration management
   - **Delivery**: April 2026

4. **Initial Testing & Documentation** 📋 *Planned*
   - Unit tests for core components
   - Integration tests with AEP sandbox
   - Developer documentation
   - **Delivery**: May 2026

**Phase 1 ETA**: **May 31, 2026**  
**Deliverable**: CLI with schema generation and basic AEP integration

---

### Phase 2: Data Ingestion (Q3 2026)
**Focus**: Batch Upload & Data Validation

#### Milestones
1. **Data Pipeline Engine** 📋 *Q3*
   - CSV/JSON/Parquet ingestion
   - Data transformation and mapping
   - Pre-ingestion validation
   - **Delivery**: July 2026

2. **Batch Ingestion Automation** 📋 *Q3*
   - Async batch upload API
   - Status monitoring and polling
   - Error handling and retry logic
   - **Delivery**: August 2026

3. **AI-Powered Data Quality** 📋 *Q3*
   - Auto-detect data issues
   - Suggest data fixes
   - Quality scoring dashboard
   - **Delivery**: September 2026

4. **Identity Resolution** 📋 *Q3*
   - AI recommends identity namespaces
   - Identity graph integration
   - Cross-dataset identity mapping
   - **Delivery**: September 2026

**Phase 2 ETA**: **September 30, 2026**  
**Deliverable**: End-to-end data ingestion with AI validation

---

### Phase 3: Scale & Adoption (Q4 2026)
**Focus**: User Experience & Team Onboarding

#### Milestones
1. **Natural Language Interface** 📋 *Q4*
   - LLM tool calling integration
   - Conversational command processing
   - Context-aware help system
   - **Delivery**: October 2026

2. **Auto-Documentation** 📋 *Q4*
   - ERD generation from schemas
   - Technical spec automation
   - Schema change tracking
   - **Delivery**: November 2026

3. **Onboarding & Training** 📋 *Q4*
   - Interactive setup wizard
   - Example workflows library
   - Video tutorials and guides
   - **Delivery**: November 2026

4. **Beta Testing Program** 📋 *Q4*
   - 5+ teams pilot program
   - Feedback collection
   - Bug fixes and refinements
   - **Delivery**: December 2026

**Phase 3 ETA**: **December 31, 2026**  
**Deliverable**: Production-ready CLI with 10+ active users

---

### Phase 4: Expansion (2027)
**Focus**: Adobe Target & Analytics Integration

#### Planned Features
- **Adobe Target** (Q1 2027)
  - Campaign automation
  - Audience segmentation with AI
  - A/B test setup wizard

- **Adobe Analytics** (Q2 2027)
  - Report generation automation
  - Data pipeline integration
  - Custom metric creation

**Phase 4 ETA**: **June 30, 2027**  
**Deliverable**: Full Adobe Experience Cloud CLI suite

---

## 📊 Project Timeline (Gantt View)

```
2026
Q1          Q2          Q3          Q4          2027 Q1-Q2
│           │           │           │           │
├─ Schema Generation ──►│           │           │
│   └─ AEP API ────────►│           │           │
│           ├─ Data Pipeline ──────►│           │
│           │   └─ Batch Ingestion ─►           │
│           │           ├─ NLP Interface ──────►│
│           │           │   └─ Auto-Docs ──────►│
│           │           │           ├─ Beta Test─►
│           │           │           │           ├─ Target Integration ──►
│           │           │           │           │   └─ Analytics ────────►
│           │           │           │           │
▼           ▼           ▼           ▼           ▼
Phase 1     Phase 2     Phase 3     Phase 4
Foundation  Ingestion   Scale       Expansion
```

---

## 🏗️ Technology Stack

### Core Framework
- **Python 3.10+** - Modern async/await, type hints
- **Typer** - CLI framework with auto-documentation
- **Rich** - Beautiful terminal UI

### AI & Intelligence
- **Anthropic Claude Sonnet 4.5** - Schema generation, data analysis
- **OpenAI GPT-4** - Alternative AI provider
- **LLM Tool Calling** - Structured API interactions

### Adobe Integration
- **httpx** - Async HTTP client for AEP APIs
- **OAuth 2.0** - Server-to-Server authentication
- **Pydantic** - XDM schema validation

### Data Processing
- **pandas** (optional) - CSV/data manipulation
- **pyarrow** (optional) - Parquet file support

*See [DEPENDENCIES.md](DEPENDENCIES.md) for complete list*

---

## 📈 Expected Impact

### Developer Efficiency
- **Before**: 10-15 hours per AEP integration project
- **After**: 2-3 hours with AI assistance
- **Time Saved**: 8-12 hours per project

### Cost Savings (Year 1)
- **20 projects/year** × 10 hours saved × $100/hour
- **Total Savings**: **$20,000 - $24,000** annually

### Team Scalability
- **Before**: 1 architect supports 3-4 projects/quarter
- **After**: 1 architect supports 10+ projects/quarter (60% self-service)
- **Capacity Increase**: **250%**

### Quality Improvements
- **95%** XDM schemas pass validation first time
- **70%** fewer configuration errors
- **80%** faster onboarding for new team members

---

## 🎯 Current Status

### ✅ Completed
- Project architecture defined
- Technology stack selected
- Coding guidelines established
- Dependencies documented

### 🔄 In Progress
- Schema generation engine (60% complete)
- XDM validation logic (40% complete)
- AI prompt engineering for schema analysis

### 📋 Next Steps (February 2026)
1. Complete XDM schema generator with AI
2. Implement AEP OAuth authentication
3. Build Schema Registry API client
4. Create first CLI command: `aep schema create`

---

## 📞 Project Information

**Project Name**: Adobe Experience Platform CLI Agent  
**Code Name**: adobe-code  
**Repository**: Internal (GitHub Enterprise)  
**Current Version**: v0.2.0 (Development)  
**Target Release**: v1.0.0 (December 2026)

**Primary KPI**: **80-85% reduction in hands-on resource time**

**Project Lead**: [Your Team]  
**Contributors**: Data Engineering, Platform Architecture  
**Stakeholders**: Customer Data teams, Integration teams

---

## 🚀 Get Involved

### For Developers
- Join beta testing program (Q4 2026)
- Contribute schemas and use cases
- Provide feedback on CLI design

### For Architects
- Review AI-generated schemas
- Define validation rules
- Share integration patterns

### For Managers
- Track cost savings metrics
- Monitor adoption rates
- Plan team onboarding

---

**Questions?** Contact the Platform Engineering team  
**Documentation**: See README.md and CLI_COMMANDS.md  
**Roadmap Updates**: Monthly status reports

---

*Last Updated: February 4, 2026*  
*Next Milestone: Schema Generation Engine (March 2026)*
