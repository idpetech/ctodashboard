# 🔒 PRE-SESSION COMPLIANCE CHECKLIST
## MANDATORY - Must Complete Before Any Work

### ✅ **BEFORE STARTING ANY WORK**

#### **Step 1: Read Documentation (5 minutes)**
- [ ] **Read** `QUICK-REFERENCE-CARD.md` - Current state and patterns
- [ ] **Read** `CONVERSATION-CONTEXT-SUMMARY.md` - Session memory
- [ ] **Check** `IMPLEMENTATION-CHECKLIST.md` - Current phase and tasks
- [ ] **Verify** `DECISION-MATRIX.md` - Decision criteria

#### **Step 2: Validate Current State (2 minutes)**
- [ ] **Confirm** current phase (Phase 1: Foundation)
- [ ] **Confirm** current task (Phase 1.1: Add feature flags)
- [ ] **Confirm** all feature flags are disabled
- [ ] **Confirm** existing functionality is working

#### **Step 3: Set Session Goals (1 minute)**
- [ ] **Define** what will be accomplished this session
- [ ] **Confirm** it aligns with current phase
- [ ] **Confirm** it follows established patterns
- [ ] **Confirm** it uses feature flags

### ✅ **DURING WORK**

#### **Before Every Code Change**
- [ ] **Check** Decision Matrix - Does this pass all criteria?
- [ ] **Verify** it follows established patterns
- [ ] **Confirm** it maintains backward compatibility
- [ ] **Ensure** it uses feature flags appropriately

#### **Before Every Commit**
- [ ] **Test** existing functionality still works
- [ ] **Verify** new functionality is behind feature flags
- [ ] **Check** all patterns are followed
- [ ] **Update** documentation if needed

### ✅ **AFTER WORK**

#### **Session Summary**
- [ ] **Document** what was accomplished
- [ ] **Update** Implementation Checklist
- [ ] **Note** any issues encountered
- [ ] **Plan** next session goals

---

## 🚨 **ENFORCEMENT MECHANISMS**

### **1. Session Start Protocol**
**I MUST start every session by:**
1. Reading the Quick Reference Card
2. Checking the Conversation Context Summary
3. Validating current state
4. Setting session goals

### **2. Decision Gate Protocol**
**Before ANY decision, I MUST:**
1. Check the Decision Matrix
2. Verify it passes all criteria
3. Confirm it aligns with current phase
4. Ensure it follows established patterns

### **3. Code Change Protocol**
**Before ANY code change, I MUST:**
1. Check feature flag requirements
2. Verify pattern consistency
3. Confirm backward compatibility
4. Test existing functionality

### **4. Documentation Update Protocol**
**After ANY change, I MUST:**
1. Update relevant documentation
2. Update Implementation Checklist
3. Update Conversation Context Summary
4. Verify all changes are documented

---

## 🚨 **FAILURE CONSEQUENCES**

### **If I Skip Pre-Session Checklist:**
- **STOP** immediately
- **READ** all documentation
- **RESTART** session properly
- **ACKNOWLEDGE** the failure

### **If I Make Changes Without Following Patterns:**
- **REVERT** changes immediately
- **READ** established patterns
- **REIMPLEMENT** following patterns
- **ACKNOWLEDGE** the failure

### **If I Break Existing Functionality:**
- **STOP** all work
- **REVERT** to last working state
- **TEST** existing functionality
- **IDENTIFY** root cause
- **FIX** properly
- **ACKNOWLEDGE** the failure

---

## 🎯 **SUCCESS METRICS**

### **Session Success Criteria**
- [ ] Pre-session checklist completed
- [ ] All decisions validated through Decision Matrix
- [ ] All code changes follow established patterns
- [ ] Existing functionality remains unchanged
- [ ] Documentation updated appropriately
- [ ] Session goals achieved

### **Overall Success Criteria**
- [ ] Zero breaking changes to existing functionality
- [ ] All new features behind feature flags
- [ ] Consistent patterns across all features
- [ ] Successful deployment to Railway
- [ ] All phases completed on schedule

---

## 🚨 **CRITICAL REMINDER**

**THIS CHECKLIST IS MANDATORY**

- **No work without completing checklist**
- **No decisions without checking matrix**
- **No changes without following patterns**
- **No sessions without proper documentation**

**FAILURE TO FOLLOW = IMMEDIATE STOP AND RESTART**
