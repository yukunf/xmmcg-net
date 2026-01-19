# Copilot Instructions for XMMCG

## Architecture Overview

**Full-stack rhythm game beatmap competition platform** with Django backend (REST API) + Vue 3 frontend (Vite).

- **Backend**: `backend/xmmcg/` - Django 6.0 project with DRF, session-based auth
- **Frontend**: `front/` - Vue 3 + Element Plus + Vite
- **Database**: SQLite (`db.sqlite3`) - development only
- **Auth**: Cookie-based sessions + CSRF tokens (not JWT)

## Core Domain Model

This is a **multi-phase competition system** for rhythm game beatmaps. Key flow:

1. **Song Upload** → Users upload songs (max 2 per user, see `MAX_SONGS_PER_USER` in [songs/models.py](backend/xmmcg/songs/models.py#L6))
2. **Bidding** → Users bid tokens on songs ([BiddingService](backend/xmmcg/songs/bidding_service.py) handles allocation)
3. **Chart Creation** → Winners create beatmaps (charts) for assigned songs
4. **Peer Review** → Automated allocation: each user reviews exactly 8 charts, receives 8 reviews
5. **Second Bidding** → Users bid on other users' partial charts to complete them

**Critical relationships**:
- `Song.user` is `ForeignKey` (one user → many songs)
- `BidResult` links user to assigned song after bidding
- `Chart.bid_result` connects charts to bidding outcomes
- `PeerReviewAllocation` ensures balanced review distribution (8 reviews per user)

## Development Workflow

### Running the Project

**Backend** (from `backend/xmmcg/`):
```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver  # or run_server.bat

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**Frontend** (from `front/`):
```bash
npm install
npm run dev  # Vite dev server on :5173
```

**Testing**:
- Run `python test_api.py` (backend root) for user API tests
- See `test_bidding_system.py`, `verify_bidding.py` for bidding tests
- Use Django Admin at `localhost:8000/admin` for data management

## Project-Specific Conventions

### Backend Patterns

1. **Service Layer**: Business logic lives in `bidding_service.py`, NOT in views
   - Example: `BiddingService.allocate_bids()` handles entire bidding allocation algorithm
   - Views are thin controllers calling service methods

2. **Tunable Constants**: All limits defined at top of [songs/models.py](backend/xmmcg/songs/models.py#L6-L13)
   ```python
   MAX_SONGS_PER_USER = 2      # Change here, not in code
   MAX_BIDS_PER_USER = 5
   PEER_REVIEW_TASKS_PER_USER = 8
   PEER_REVIEW_MAX_SCORE = 50
   ```

3. **Phase Management**: Competition phases controlled by `CompetitionPhase` model
   - `phase_key` field (e.g., 'bidding', 'mapping', 'peer_review') drives frontend route guards
   - `page_access` JSONField controls which pages are accessible during each phase
   - Status computed in real-time: [models.py#L320-329](backend/xmmcg/songs/models.py) `status` property

4. **File Handling**: Audio files stored in `media/songs/`, but **chart files are external**
   - `Chart.chart_url` points to external beatmap server
   - Frontend downloads from external, submits URL reference back

5. **CSRF Protection**: Required for all POST/PUT/DELETE requests
   - Frontend must call `ensureCsrfToken()` before mutations (see [api/index.js](front/src/api/index.js#L90))
   - Token in cookie, sent as `X-CSRFToken` header

### Frontend Patterns

1. **API Client**: Centralized in `src/api/index.js` with axios interceptors
   - Auto-attaches CSRF token from cookies
   - Error handling with Element Plus messages
   - Base URL configured via `window.API_BASE_URL`

2. **Route Guards**: Phase-based access control in router
   - Check `CompetitionPhase.page_access` to enable/disable routes
   - Example: Charts page locked until mapping phase starts

3. **Components**:
   - `PhaseTimeline.vue` - Shows competition progress
   - `Banner.vue`, `Announcement.vue` - Admin-controlled homepage content
   - Views in `src/views/` correspond to main pages (Songs, Charts, Profile)

## Key Integration Points

### Backend ↔ Frontend Contract

**Authentication**:
- `POST /api/users/login/` → Sets session cookie
- All authenticated endpoints require session cookie
- Frontend stores username in localStorage for UI, but auth is server-side session

**Bidding Flow**:
1. Frontend: `POST /api/songs/bidding/current/` - Check if round active
2. User places bids: `POST /api/songs/bids/` (validated against `MAX_BIDS_PER_USER`)
3. Admin triggers: `POST /api/songs/bidding/{round_id}/allocate/` (server-side only)
4. Users see results: `GET /api/songs/bid-results/me/`

**Phase Queries**:
- `GET /api/songs/phases/` - All phases with real-time status
- `GET /api/songs/phase/current/` - Active phase for route guards

## Common Pitfalls

- **Don't modify Song.user back to OneToOneField** - It's intentionally ForeignKey for multi-upload
- **Peer review allocation is automatic** - Admin calls `POST /api/songs/peer-review/{round_id}/allocate/`, algorithm guarantees exactly 8 tasks per user
- **Chart files are NOT uploaded to Django** - Only store URL references
- **CORS is configured** - But only for localhost:3000 and localhost:5173 ([settings.py#L137-142](backend/xmmcg/xmmcg/settings.py#L137-142))
- **Phase-locked features** - Check CompetitionPhase before enabling new features

## Documentation References

- [BIDDING_SYSTEM_GUIDE.md](BIDDING_SYSTEM_GUIDE.md) - Complete bidding algorithm explanation
- [PEER_REVIEW_SYSTEM.md](PEER_REVIEW_SYSTEM.md) - Peer review allocation logic
- [COMPETITION_PHASE_SYSTEM.md](COMPETITION_PHASE_SYSTEM.md) - Phase management details
- [backend/xmmcg/README.md](backend/xmmcg/README.md) - User auth system guide

## Admin Tasks

Use Django Admin (`/admin`) for:
- Creating BiddingRounds and triggering allocation
- Managing CompetitionPhases (control phase timing and page access)
- Creating Banners/Announcements for homepage
- Viewing all competition data (bids, charts, reviews)
