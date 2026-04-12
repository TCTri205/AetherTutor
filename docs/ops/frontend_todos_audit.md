# Frontend TODOs Audit

> Date: 2026-04-12
> Sprint: 19, Task 11
> Scope: `frontend/src/`

## Summary
- Total TODOs found: **2** (1 false positive excluded: `navigateToDocGraph` in GlobalGraphExplorer.tsx contains "To" but is not a TODO comment)
- High priority: **1**
- Medium priority: **1**
- Low priority: **0**

## TODOs List

| # | File | Line | TODO | Assigned To | Severity | Status |
|---|------|------|------|-------------|----------|--------|
| 1 | `components/shared/ContextChips.tsx` | 24 | `// TODO: Truyền entity name sang Graph page qua state/params` | Sprint 19, Task 12 (Graph Navigation) | Medium | **PENDING** - Code đã truyền `state: { highlightEntity: entityName }` qua navigate, nhưng Graph page cần implement việc đọc state này và highlight node tương ứng |
| 2 | `components/shared/ErrorBoundary.tsx` | 38 | `// TODO: Send to error tracking service (Sentry, etc.)` | Sprint 20, Task 3 (Observability) | High | **PENDING** - Code đã có comment hướng dẫn nhưng chưa có integration thực tế với Sentry hay service tương tự |

## Detailed Analysis

### 1. ContextChips.tsx:24 - Entity Navigation State

**File:** `D:\Projects_IT\AetherTutor\frontend\src\components\shared\ContextChips.tsx`
**Line:** 24
**TODO Text:** `// TODO: Truyền entity name sang Graph page qua state/params`

**Current Implementation:**
```typescript
navigate(`/graph/${documentId}`, {
  state: { highlightEntity: entityName }
});
```

**Analysis:**
- ContextChips component đã thực hiện việc truyền `highlightEntity` qua React Router state.
- Vấn đề còn lại: **Graph page** (DocumentGraphViewer hoặc GraphPage) cần:
  1. Đọc `highlightEntity` từ `location.state`
  2. Tìm node tương ứng trong graph data
  3. Apply visual highlight (zoom, color change, pulse animation)
  4. Clear highlight sau khi user interact

**Assigned To:** Sprint 19, Task 12 - Graph Navigation Enhancement
**Severity:** Medium (functionality hoạt động nhưng UX chưa hoàn thiện)

---

### 2. ErrorBoundary.tsx:38 - Error Tracking Service Integration

**File:** `D:\Projects_IT\AetherTutor\frontend\src\components\shared\ErrorBoundary.tsx`
**Line:** 38
**TODO Text:** `// TODO: Send to error tracking service (Sentry, etc.)`

**Current Implementation:**
```typescript
public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
  console.error('Uncaught error:', error, errorInfo);

  if (this.props.onError) {
    this.props.onError(error, errorInfo);
  }

  // TODO: Send to error tracking service (Sentry, etc.)
  // if (process.env.NODE_ENV === 'production') {
  //   sendToSentry(error, errorInfo);
  // }
}
```

**Analysis:**
- Error boundary đã có fallback UI và console logging.
- Có callback prop `onError` để parent component xử lý.
- **Chưa có** integration với bất kỳ error tracking service nào.
- Comment đã có code mẫu cho Sentry nhưng chưa implement.

**Assigned To:** Sprint 20, Task 3 - Observability & Monitoring
**Severity:** High (production không có error tracking = blind debugging)

---

## Completed TODOs

### Stage 4 TODOs (Sprint 1-18)
- Không có TODO nào khác được tìm thấy trong `frontend/src/` ngoài 2 TODOs trên.
- Tất cả các TODOs từ các sprint trước đã được resolve hoặc không còn tồn tại.

### False Positives (Excluded)
- `GlobalGraphExplorer.tsx:153` - `navigateToDocGraph` function name chứa "To" nhưng không phải TODO comment.

---

## Recommendations

### Immediate Actions (Sprint 19)

1. **Implement Graph Highlight Navigation** (Task 12)
   - Đọc `location.state.highlightEntity` trong DocumentGraphViewer/GraphPage
   - Implement visual highlight cho node tương ứng:
     - Zoom to node
     - Change node color/border
     - Add pulse animation
     - Show node details panel
   - Clear highlight on graph interaction

   **Estimated Effort:** 2-3 hours

2. **Convert ContextChips TODO to Ticket**
   - Create ticket: "Graph Page - Read highlightEntity from location.state"
   - Link to ContextChips.tsx implementation
   - Add acceptance criteria

### Short-term (Sprint 20)

3. **Error Tracking Integration** (Task 3)
   - Options:
     - **Sentry** (recommended): Full-featured, free tier generous
     - **LogRocket**: Session replay + error tracking
     - **Custom**: Log to backend PostgreSQL via API
   - Install SDK: `npm install @sentry/react @sentry/browser`
   - Initialize in `main.tsx` or `App.tsx`
   - Update ErrorBoundary to call Sentry
   - Add source maps for production debugging

   **Estimated Effort:** 4-6 hours

4. **Add Environment-Based Error Reporting**
   ```typescript
   if (import.meta.env.PROD) {
     Sentry.captureException(error, { contexts: { react: errorInfo } });
   }
   ```

### Long-term (Stage 5+)

5. **Performance Monitoring**
   - Add React Profiler integration
   - Track slow renders
   - Monitor LCP, FCP, CLS metrics

6. **User Session Tracking**
   - Link errors to user sessions
   - Reproduce user-reported issues
   - Add breadcrumbs for debugging

---

## TODOs to Convert to Tickets

| Ticket Title | Priority | Sprint | Estimated Hours |
|-------------|----------|--------|-----------------|
| Graph Page: Read highlightEntity from location.state and apply visual highlight | Medium | 19 | 2-3 |
| Integrate Sentry for production error tracking | High | 20 | 4-6 |
| Add React Profiler for performance monitoring | Low | 21+ | 3-4 |

---

## Audit Metadata

- **Performed by:** Qwen Code Agent
- **Date:** 2026-04-12
- **Sprint:** 19
- **Task:** 11
- **Tools used:** grep_search, read_file
- **Files scanned:** All files in `D:\Projects_IT\AetherTutor\frontend\src\`
- **Patterns searched:** `TODO`, `FIXME`, `HACK`
