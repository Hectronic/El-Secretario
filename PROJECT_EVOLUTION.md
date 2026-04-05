# Secretario Project Evolution Guide

This guide summarizes the development history and evolution of the **Secretario** application, based on the implementation plans and walkthroughs created during its development.

## Timeline of Changes

### 1. Collections Explorer & Chat History (Jan 4, 2026)
**Goal**: Enhance content organization and chat experience.
- **Features**:
    - **Collections Explorer**: Added a new section in the right panel to view recordings by "Collection" (Tag).
    - **Collection Widget**: Created a dedicated view for a collection, allowing users to chat with the context of that specific collection.
    - **Chat History**: Improved the UI by hiding the scrollbar for a cleaner look.
- **Technical**: Updated `RAGEngine` to support tag-based filtering (`$contains`).

### 2. UI Style Adjustments (Jan 5, 2026)
**Goal**: Improve visual consistency with the dark theme.
- **Features**:
    - **Dark Theme Lists**: Updated Sidebar History and Welcome Screen Favorites to use a dark background with readable light text.
    - **Styling**: Centralized styles in `ui/styles.py`.

### 3. Unit Testing Infrastructure (Jan 6, 2026)
**Goal**: Ensure code stability and reliability.
- **Features**:
    - **Test Suite**: Created `tests/` directory with tests for Database, RAG Engine, Audio Recorder, and Worker threads.
    - **Test Runner**: Implemented `run_with_test.sh` to automatically discover and run all tests.

### 4. Calendar Feature (Jan 12, 2026)
**Goal**: Allow time-based navigation of recordings.
- **Features**:
    - **Calendar Tab**: Added a new main tab with a calendar interface.
    - **Date Filtering**: Users can select a date to view recordings from that day.
    - **Chat Context**: Integrated date selection into the RAG chat context.

### 5. Favorites Filter (Jan 13, 2026)
**Goal**: Quick access to important recordings.
- **Features**:
    - **Sidebar Filter**: Added a "Favorites" filter to the sidebar history.
    - **Welcome Screen**: Displayed favorited items on the Welcome Screen.

### 6. Batch Processing (Jan 15, 2026)
**Goal**: Automate the processing of backlog recordings.
- **Features**:
    - **Batch Widget**: Created `BatchProcessWidget` to manage the queue of pending recordings.
    - **Process Pending**: Added a button to the Welcome Screen to start processing all undiarized recordings.
    - **Logic**: Uses "large-v3" model and enables diarization for batch tasks.

### 7. Import Audio (Jan 16, 2026)
**Goal**: Allow importing external audio files.
- **Features**:
    - **Import Button**: Added "Import Audio" to the Welcome Screen.
    - **Workflow**: Copies selected file to `recordings/`, creates a DB entry, and automatically starts transcription.

### 8. Manual Diarization Toggle (Jan 16, 2026)
**Goal**: Give users control over diarization status.
- **Features**:
    - **Checkbox**: Added a "Diarized" checkbox to the Recording Widget metadata.
    - **Database**: Updated schema and logic to allow manual toggling of the `is_diarized` flag.

### 9. Test Runner Improvements (Jan 17, 2026)
**Goal**: Fix crashes and improve test reliability.
- **Fixes**:
    - Resolved Segmentation Faults caused by `sounddevice` and `PyQt` conflicts during testing.
    - Created `verify_pipeline.sh` for a complete verification workflow (tests + orphan checks).

### 10. UI Layout Adjustments (Jan 18, 2026)
**Goal**: Optimize screen real estate.
- **Features**:
    - **Right Column**: Increased the default width and minimum width of the right panel (Chat/Collections) to ensure it remains usable.

### 11. Calendar Multi-Selection (Jan 19, 2026)
**Goal**: Flexible date selection.
- **Features**:
    - **Multi-Select**: Enabled Ctrl+Click (toggle) and Shift+Click (range) in the Calendar.
    - **Context**: Chat and list views now reflect the entire selection of dates.

### 12. Resilient Batch Processing (Jan 20, 2026)
**Goal**: Improve stability of long-running batch tasks.
- **Features**:
    - **Error Handling**: Failed items are now kept in the list and marked as "Failed" (red) instead of being silently removed.
    - **Memory Management**: Explicitly frees memory (garbage collection) between batch items to prevent leaks.

### 13. Local Setup Documentation (Jan 21, 2026)
**Goal**: Ease of onboarding.
- **Features**:
    - Documented steps to run the application locally.

### 14. Floating Chat UI Improvements (March 12, 2026)
**Goal**: Fix alignment and overlapping issues in the floating chat bar.
- **Features**:
    - **Right Alignment**: Floating chats now align to the bottom right of the window for better accessibility.
    - **Transparent Bar**: Removed the shared background/border from the bar, making each chat look like an independent floating window.
    - **Better Resizing**: Improved logic for minimizing/restoring chats, ensuring the bar repositions correctly when its size changes.
    - **Compact Layout**: Reduced the default width and improved spacing to prevent clutter.
    - **Adaptive Theme Support**: Colors, borders, and buttons now adapt automatically to Light/Dark themes. Fixed an issue where the floating window background remained white in dark mode by using explicit theme-aware background colors and robust theme detection.

---

## Related Side Projects
During this period, some work was also done on separate utilities in the `bash-scripts` repository:
- **GitLab User Activity Reporter**: A tool to generate HTML activity reports for GitLab users.
- **GitLab User Registration**: A script to batch register users in GitLab.
