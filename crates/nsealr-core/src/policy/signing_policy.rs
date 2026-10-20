//! Profile-specific local diagnostics; these never enable production signing.
//!
//! The old twelve-boolean universal readiness/development-waiver API is retired.
//! Typed local observations and profile blockers live in the portable model.
//! No report, assessment or policy module can construct consuming consent.

pub use crate::capabilities::{
    assess_profile, AssessmentContext, Blocker, BlockerReason, LocalAssessment, LocalObservations,
    ProfileAssessment, Requirement, Verification,
};
