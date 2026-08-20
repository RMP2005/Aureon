"""Hospital and emergency medical facility models.

Models hospital specialties, capacity, trauma center tiers,
and dynamic receiving suitability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HospitalSpecialty(str, Enum):
    """Clinical capabilities of receiving hospitals."""

    GENERAL_EMERGENCY = "general_emergency"
    LEVEL_1_TRAUMA = "level_1_trauma"
    LEVEL_2_TRAUMA = "level_2_trauma"
    CARDIAC_CATH_LAB = "cardiac_cath_lab"
    STROKE_COMPREHENSIVE = "stroke_comprehensive"
    BURN_ICU = "burn_icu"
    PEDIATRIC_ICU = "pediatric_icu"


@dataclass
class PatientStay:
    """Tracks an active patient stay in the hospital."""

    incident_id: str
    bed_type: str  # "er" or "icu"
    admitted_at_sec: float
    stay_duration_sec: float


@dataclass
class Hospital:
    """Medical center capable of receiving emergency patients."""

    id: str
    name: str
    node_id: str
    latitude: float
    longitude: float
    specialties: list[HospitalSpecialty] = field(default_factory=list)
    total_er_beds: int = 30
    occupied_er_beds: int = 10
    total_icu_beds: int = 15
    occupied_icu_beds: int = 5
    avg_triage_time_min: float = 8.0  # Time to handover patient
    avg_stay_duration_seconds: float = 7200.0  # Average patient stay (2 hours)
    is_diverting: bool = False  # If true, hospital is not accepting new severe emergencies
    metadata: dict[str, Any] = field(default_factory=dict)

    # Active patient tracking for discharge scheduling
    _active_patients: list[PatientStay] = field(default_factory=list, repr=False)

    @property
    def active_patient_count(self) -> int:
        """Number of patients currently admitted."""
        return len(self._active_patients)

    def admit_patient(
        self,
        incident_id: str,
        bed_type: str,
        current_time_sec: float,
        stay_duration_sec: float | None = None,
    ) -> bool:
        """Admit a patient and occupy a bed. Returns True if admission succeeded."""
        duration = stay_duration_sec or self.avg_stay_duration_seconds

        if bed_type == "icu":
            if self.occupied_icu_beds >= self.total_icu_beds:
                return False
            self.occupied_icu_beds += 1
        else:
            if self.occupied_er_beds >= self.total_er_beds:
                return False
            self.occupied_er_beds += 1

        self._active_patients.append(
            PatientStay(
                incident_id=incident_id,
                bed_type=bed_type,
                admitted_at_sec=current_time_sec,
                stay_duration_sec=duration,
            )
        )
        return True

    def process_discharges(self, current_time_sec: float) -> int:
        """Release beds for patients whose stay has completed. Returns count discharged."""
        still_active: list[PatientStay] = []
        discharged = 0

        for patient in self._active_patients:
            elapsed = current_time_sec - patient.admitted_at_sec
            if elapsed >= patient.stay_duration_sec:
                if patient.bed_type == "icu":
                    self.occupied_icu_beds = max(0, self.occupied_icu_beds - 1)
                else:
                    self.occupied_er_beds = max(0, self.occupied_er_beds - 1)
                discharged += 1
            else:
                still_active.append(patient)

        self._active_patients = still_active
        return discharged

    @property
    def er_occupancy_ratio(self) -> float:
        """Ratio of occupied ER beds to total ER beds."""
        if self.total_er_beds == 0:
            return 1.0
        return self.occupied_er_beds / self.total_er_beds

    @property
    def has_icu_capacity(self) -> bool:
        """Check if ICU beds are available for critical patients."""
        return self.occupied_icu_beds < self.total_icu_beds

    def supports_specialty(self, specialty: HospitalSpecialty) -> bool:
        """Check if hospital provides a specific clinical specialty."""
        return specialty in self.specialties

    def calculate_suitability_score(
        self,
        incident_category: str,
        is_critical: bool,
    ) -> float:
        """Calculate clinical suitability score (0.0 to 1.0) for an emergency.

        Considers specialty match, bed availability, and diversion status.
        """
        if self.is_diverting:
            return 0.1

        score = 0.5  # Base general score

        # Specialty matching bonuses
        if "cardiac" in incident_category.lower():
            if self.supports_specialty(HospitalSpecialty.CARDIAC_CATH_LAB):
                score += 0.4
        elif "stroke" in incident_category.lower():
            if self.supports_specialty(HospitalSpecialty.STROKE_COMPREHENSIVE):
                score += 0.4
        elif "trauma" in incident_category.lower() or "collision" in incident_category.lower():
            if self.supports_specialty(HospitalSpecialty.LEVEL_1_TRAUMA):
                score += 0.4
            elif self.supports_specialty(HospitalSpecialty.LEVEL_2_TRAUMA):
                score += 0.25

        # Capacity penalties
        if is_critical and not self.has_icu_capacity:
            score -= 0.35

        # Heavy ER congestion penalty
        if self.er_occupancy_ratio > 0.9:
            score -= 0.2
        elif self.er_occupancy_ratio > 0.75:
            score -= 0.1

        return max(0.05, min(1.0, score))


def get_default_bangalore_hospitals() -> list[Hospital]:
    """Pre-configured list of realistic premier hospitals in Bangalore."""
    return [
        Hospital(
            id="hosp_manipal_hal",
            name="Manipal Hospital HAL",
            node_id="node_manipal_hosp",
            latitude=12.9583,
            longitude=77.6486,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_1_TRAUMA,
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=40,
            occupied_er_beds=18,
            total_icu_beds=25,
            occupied_icu_beds=12,
        ),
        Hospital(
            id="hosp_st_johns",
            name="St. John's Medical College & Hospital",
            node_id="node_st_johns_hosp",
            latitude=12.9318,
            longitude=77.6186,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_1_TRAUMA,
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.PEDIATRIC_ICU,
            ],
            total_er_beds=50,
            occupied_er_beds=28,
            total_icu_beds=30,
            occupied_icu_beds=18,
        ),
        Hospital(
            id="hosp_narayana_health",
            name="Narayana Health City (Cardiac Specialty)",
            node_id="node_narayana_health",
            latitude=12.8182,
            longitude=77.6914,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.LEVEL_1_TRAUMA,
            ],
            total_er_beds=45,
            occupied_er_beds=15,
            total_icu_beds=35,
            occupied_icu_beds=14,
        ),
        Hospital(
            id="hosp_apollo_bannerghatta",
            name="Apollo Hospital Bannerghatta",
            node_id="node_apollo_bannerghatta",
            latitude=12.8954,
            longitude=77.5986,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_1_TRAUMA,
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=35,
            occupied_er_beds=16,
            total_icu_beds=20,
            occupied_icu_beds=9,
        ),
        Hospital(
            id="hosp_aster_cmi",
            name="Aster CMI Hospital Hebbal",
            node_id="node_aster_cmi_hosp",
            latitude=13.0560,
            longitude=77.5919,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_1_TRAUMA,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
                HospitalSpecialty.CARDIAC_CATH_LAB,
            ],
            total_er_beds=35,
            occupied_er_beds=12,
            total_icu_beds=20,
            occupied_icu_beds=8,
        ),
        Hospital(
            id="hosp_vydehi",
            name="Vydehi Super Specialty Hospital",
            node_id="node_vydehi_hosp",
            latitude=12.9754,
            longitude=77.7291,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
                HospitalSpecialty.CARDIAC_CATH_LAB,
            ],
            total_er_beds=30,
            occupied_er_beds=10,
            total_icu_beds=15,
            occupied_icu_beds=6,
        ),
    ]
