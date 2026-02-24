# Dental PMS Integration - Technical Assessment

**Time Limit**: 4 hours

**Important**: This assessment contains more work than can reasonably be completed. That's intentional. We want to see how you prioritize, what you tackle first, what you cut, and how you communicate those trade-offs. Don't try to do everything perfectly — show us what you think matters most.

---

## Part 1: Build an API Wrapper

### Background

You're joining a dental AI company that automates front desk operations via phone AI. One of our biggest challenges is integrating with legacy Practice Management Systems (PMS) that dental clinics use.

DentalTrack Pro is a legacy PMS from 2010 that many of our clinic customers rely on. During phone calls, our AI needs to look up patients, check appointment availability, and book appointments — all in real time while someone is on the phone.

The legacy system is slow, unreliable, and poorly documented — much like the real PMS systems you'd work with on this team.

### The Legacy API

The DentalTrack Pro API is running at: `https://takehome-production.up.railway.app/`

That's all the documentation you're going to get. The original vendor went out of business years ago and the docs went with them. Part of this job is figuring out how unfamiliar systems work.

Start by exploring the API. Document what you find.

### Your Task

Build a REST API wrapper (using Flask, FastAPI, Express.js, or a framework of your choice) that our voice system can reliably call during live phone calls. Your API should run on **port 3000**.

#### Endpoints to Build

**1. `GET /api/v1/patients/:phone_number`**

Our voice AI captures the caller's phone number from the incoming call. It needs to quickly pull up the patient's info — name, contact, date of birth, insurance status, and when they last came in.

Callers' phone numbers come in all kinds of formats. Your API should handle that gracefully.

All dates should come back as `YYYY-MM-DD`. Booleans should be actual booleans. Phone numbers should be in a consistent format.

Response time matters — a patient is on the phone waiting. **Must respond in under 2 seconds.**

**2. `GET /api/v1/appointments/availability`**

During the call, patients want to know when they can come in. The voice AI needs to check available slots.

Query Parameters:
- `date` (required): `YYYY-MM-DD`
- `dentist_id` (optional): filter by a specific dentist

Return available time slots with the time, dentist ID, and dentist name.

**3. `POST /api/v1/appointments/book`**

Once the patient picks a slot, the voice AI books it. Your API should handle the obvious failure cases — what if the patient doesn't exist? What if someone else just booked that slot? What if the voice AI accidentally sends the same booking request twice?

Request body should include: patient ID, dentist ID, date, time, and reason for visit.

### What You're Given

- `test_requirements.py` — Test cases your API must pass. Read them carefully.
- The legacy API endpoint above.

You build everything else from scratch.

---

## Part 2: System Architecture Design

We currently have one integration (the DentalTrack Pro wrapper you just built). In reality, dental clinics use many different PMS systems, and we need to support multiple integrations.

**Your task**: Design the backend architecture for a system that allows our voice AI to integrate with multiple PMS platforms. Specifically, consider these two real systems in addition to DentalTrack Pro:

- **Dentrix** — The most widely used dental PMS in North America. It's an on-premise Windows desktop application with no cloud API. Think about what that means for integration.
- **OpenDental** — An open-source dental PMS with a documented API. Their documentation is publicly available at [opendental.com/site/apioverview.html](https://opendental.com/site/apioverview.html). Take a look.

Write a `SYSTEM_DESIGN.md` that addresses:

1. **Multi-PMS Architecture**: How does your system handle the fact that different clinics use different PMS software? What's the abstraction layer? How do you add support for a new PMS without rewriting your voice AI integration?

2. **The On-Premise Problem**: Dentrix runs on a Windows machine inside the clinic. It has no public API. How does your system communicate with it? What software needs to run at the clinic? How is it deployed and updated? What happens when the clinic's internet drops during a patient call?

3. **Data Model**: Our voice AI needs the same information (patients, appointments, availability) regardless of which PMS a clinic uses. How do you normalize across systems that store data completely differently? What's your canonical data model?

4. **Reliability During Live Calls**: A patient is on the phone. What happens when the PMS is slow? When the clinic's internet goes down? When your integration crashes mid-call? What degrades gracefully vs. what fails hard?

5. **Database & Caching Strategy**: What do you store on your side vs. what do you fetch in real-time from the PMS? What are the consistency trade-offs? When is stale data acceptable and when is it dangerous?

Be specific. "We'd use an adapter pattern" is a starting point, not an answer. What does the adapter do? What interface does it implement? "We'd deploy a local agent" — what does the agent run on? How does it authenticate? What happens when it crashes at 2 AM and the clinic opens at 8?

Your document should be detailed enough that another engineer could read it and start building. Include diagrams if they help. We'd rather see a deep treatment of two or three sections than a shallow pass across all five.

---

## Evaluation Criteria

### Part 1 — API Wrapper (50%)
1. **Functionality**: Do the endpoints work? Do the tests pass?
2. **Code Quality**: Is the code clean, documented, and maintainable?
3. **Error Handling**: The legacy API *will* fail on you. How does your wrapper handle it?

### Part 2 — System Design (30%)
1. **Depth of Thinking**: Did you wrestle with the hard problems (on-prem, reliability, multi-tenant)?
2. **Practical Trade-offs**: Do you acknowledge what's hard and make reasonable compromises?
3. **Real-World Awareness**: Did you actually look at how Dentrix and OpenDental work, or did you hand-wave?

### Overall (20%)
1. **Prioritization**: Given limited time, did you focus on what matters?
2. **Communication**: Can you explain your decisions and what you'd do differently?
3. **Pragmatism**: Perfect is the enemy of done.

---

## What We're Looking For

- **Senior-level thinking**: Anticipating problems, not just handling the happy path
- **Production mindset**: This isn't a toy — could you deploy this and sleep at night?
- **Honest communication**: Tell us what you cut, what you'd do next, and why
- **Your perspective**: We want to see how *you* think about these problems, not a textbook answer

---

## Submission

Push your code to this repository. Include:

- Working API that passes the test suite (or as much as you got working)
- `ARCHITECTURE.md` — explain your key technical decisions for the wrapper
- `EXPLORATION.md` — document your process discovering the legacy API. **Include your actual terminal history** (copy-paste from your terminal, screenshots, or shell history export). We want to see your real process — wrong turns, failed attempts, and all. A polished narrative is less valuable than raw evidence of how you actually worked.
- `SYSTEM_DESIGN.md` — your multi-PMS architecture design
- At least 2 additional edge case tests you think are important
- A note on how you spent your 4 hours and what you'd do with more time

Good luck! 🦷
