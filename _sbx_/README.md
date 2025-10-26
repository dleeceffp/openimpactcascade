# AI Chat Assistant - Implementation Guide

## Overview

Adds a contextual AI chat assistant sidebar that helps users understand and complete the risk assessment questionnaire in real-time.

## Features

### 1. **Context-Aware Help**
- Automatically updates based on current question
- Provides specific guidance for LEF, LM, and control assessments
- Remembers conversation history (last 3 exchanges)

### 2. **Quick Help Buttons**
Dynamically generated based on question type:

**For Loss Event Frequency:**
- "How to estimate frequency?"
- "Typical frequencies"
- "Explain min/mode/max"

**For Loss Magnitude:**
- "What costs to include?"
- "How to estimate impact"
- "Explain ranges"

**For Security Controls:**
- "Prevention controls?"
- "Detection controls?"
- "How to improve?"

### 3. **Conversational AI**
- Uses Claude Sonnet 4 for responses
- Tailored to user's industry and region
- Explains concepts in simple language
- Provides practical examples

### 4. **Responsive Design**
- **Desktop:** Persistent sidebar (400px wide)
- **Mobile:** Collapsible sidebar with floating button

## Implementation

### Step 1: Update Flask App

Add the `/chat/assist` endpoint to `flask_app.py` (already included in updated artifact).

### Step 2: Replace Questionnaire Template

**Option A: Replace existing template**
```bash
cd ~/oic/OIC_SBX/anthropic/templates
cp questionnaire.html questionnaire_backup.
