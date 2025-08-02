# Architecture Decisions and Thoughts

## Technology Stack Rationale
- **Streamlit**: Chosen per spec preference. Good for rapid prototyping and data apps
- **SQLite**: Perfect for local-first approach, no server setup needed
- **Pandas**: Excellent for CSV parsing and data manipulation
- **Plotly**: Integrates well with Streamlit, interactive charts

## Key Design Decisions
1. **Local-First Architecture**: All data stays on user's machine, no cloud dependencies
2. **Single-Page App**: Streamlit's natural pattern, simple navigation
3. **Immediate Persistence**: Changes save to database immediately, no "save" buttons needed
4. **Flexible Categories**: User-defined categories with auto-suggestions

## Potential Challenges
1. **Large CSV Files**: Need to handle memory efficiently with pandas
2. **Concurrent Access**: SQLite locking if multiple users (unlikely for local app)
3. **Date Parsing**: Different date formats in CSV files
4. **Category Management**: Avoiding category proliferation, providing good UX

## Implementation Order Rationale
Starting with data layer (models, database) before UI ensures solid foundation. CSV parsing comes early since it's core to the value proposition. UI framework setup enables iterative development of features.

## Future Extensibility Considerations
- Plugin architecture for different bank formats
- Export functionality (PDF reports, etc.)
- Budgeting and goal-setting features
- Receipt attachment support