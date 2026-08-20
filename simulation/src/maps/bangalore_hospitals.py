"""Bangalore hospital dataset: real locations, simulated capacity.

This module provides curated hospital datasets for the Aureon simulation
at three scales (small / medium / large).

What is REAL in this file:
    * Hospital names refer to genuine, well-known medical institutions
      in Bengaluru, Karnataka, India.
    * Latitude/longitude pairs approximate the real-world geographic
      positions of those institutions.

What is SIMULATED in this file:
    * Every capacity figure -- ER bed counts, ICU bed counts, current
      occupancy levels, triage times, and stay durations -- is a
      SYNTHETIC value created purely for simulation purposes. These are
      explicitly marked below as "SIMULATION CONFIGURATION".
"""

from __future__ import annotations

from ..models.hospital import (
    Hospital,
    HospitalSpecialty,
    get_default_bangalore_hospitals,
)

_SCALE_SMALL = "small"
_SCALE_MEDIUM = "medium"
_SCALE_LARGE = "large"
_VALID_SCALES: tuple[str, ...] = (_SCALE_SMALL, _SCALE_MEDIUM, _SCALE_LARGE)


def _build_hospital(
    *,
    hospital_id: str,
    name: str,
    latitude: float,
    longitude: float,
    specialties: list[HospitalSpecialty],
    total_er_beds: int,
    occupied_er_beds: int,
    total_icu_beds: int,
    occupied_icu_beds: int,
    avg_triage_time_min: float = 8.0,
) -> Hospital:
    """Construct a Hospital record from a compact specification.

    NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
    They are not real-world verified data. Do not cite as factual.

    Args:
        hospital_id: Short slug (e.g. "nimhans"); full id and node_id are
            derived from it following the project naming convention.
        name: Real institution name.
        latitude: Real approximate latitude of the institution.
        longitude: Real approximate longitude of the institution.
        specialties: Clinical capabilities offered.
        total_er_beds: SIMULATION CONFIGURATION (synthetic).
        occupied_er_beds: SIMULATION CONFIGURATION (synthetic initial load).
        total_icu_beds: SIMULATION CONFIGURATION (synthetic).
        occupied_icu_beds: SIMULATION CONFIGURATION (synthetic initial load).
        avg_triage_time_min: SIMULATION CONFIGURATION (synthetic handover time).

    Returns:
        A fully configured Hospital instance.
    """
    return Hospital(
        id=f"hosp_{hospital_id}",
        name=name,
        node_id=f"node_{hospital_id}_hosp",
        latitude=latitude,
        longitude=longitude,
        specialties=specialties,
        total_er_beds=total_er_beds,
        occupied_er_beds=occupied_er_beds,
        total_icu_beds=total_icu_beds,
        occupied_icu_beds=occupied_icu_beds,
        avg_triage_time_min=avg_triage_time_min,
        metadata={"capacity_source": "SIMULATION CONFIGURATION"},
    )


def _get_medium_additions() -> list[Hospital]:
    """Nine additional real Bangalore hospitals beyond the small dataset.

    NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
    They are not real-world verified data. Do not cite as factual.
    """
    # ------------------------------------------------------------------
    # SIMULATION CONFIGURATION: every numeric capacity value below is
    # synthetic. Names and coordinates reference real institutions.
    # ------------------------------------------------------------------
    return [
        _build_hospital(
            hospital_id="nimhans",
            name="NIMHANS (National Institute of Mental Health and Neuro Sciences)",
            latitude=12.9416,
            longitude=77.5946,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=45,
            occupied_er_beds=20,
            total_icu_beds=30,
            occupied_icu_beds=14,
            avg_triage_time_min=10.0,
        ),
        _build_hospital(
            hospital_id="bowring_lady_curzon",
            name="Bowring & Lady Curzon Hospital",
            latitude=12.9838,
            longitude=77.6084,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=35,
            occupied_er_beds=15,
            total_icu_beds=18,
            occupied_icu_beds=8,
            avg_triage_time_min=9.0,
        ),
        _build_hospital(
            hospital_id="victoria",
            name="Victoria Hospital",
            latitude=12.9608,
            longitude=77.5787,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=60,
            occupied_er_beds=32,
            total_icu_beds=40,
            occupied_icu_beds=22,
            avg_triage_time_min=12.0,
        ),
        _build_hospital(
            hospital_id="ms_ramaiah_memorial",
            name="M.S. Ramaiah Memorial Hospital",
            latitude=13.0274,
            longitude=77.5443,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
                HospitalSpecialty.CARDIAC_CATH_LAB,
            ],
            total_er_beds=40,
            occupied_er_beds=18,
            total_icu_beds=28,
            occupied_icu_beds=13,
            avg_triage_time_min=9.0,
        ),
        _build_hospital(
            hospital_id="jayadeva",
            name="Sri Jayadeva Institute of Cardiovascular Sciences",
            latitude=12.9184,
            longitude=77.5979,
            specialties=[
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=30,
            occupied_er_beds=14,
            total_icu_beds=35,
            occupied_icu_beds=18,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="rainbow_marathahalli",
            name="Rainbow Children's Hospital Marathahalli",
            latitude=12.9571,
            longitude=77.6983,
            specialties=[
                HospitalSpecialty.PEDIATRIC_ICU,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=20,
            occupied_er_beds=8,
            total_icu_beds=14,
            occupied_icu_beds=6,
            avg_triage_time_min=7.0,
        ),
        _build_hospital(
            hospital_id="columbia_asia_hebbal",
            name="Columbia Asia Hospital Hebbal",
            latitude=13.0433,
            longitude=77.5927,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=30,
            occupied_er_beds=12,
            total_icu_beds=18,
            occupied_icu_beds=8,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="gleneagles_global",
            name="Gleneagles Global Hospital",
            latitude=12.9165,
            longitude=77.6031,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=35,
            occupied_er_beds=16,
            total_icu_beds=25,
            occupied_icu_beds=12,
            avg_triage_time_min=9.0,
        ),
        _build_hospital(
            hospital_id="motherhood_koramangala",
            name="Motherhood Hospital Koramangala",
            latitude=12.9338,
            longitude=77.6260,
            specialties=[
                HospitalSpecialty.PEDIATRIC_ICU,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=15,
            occupied_er_beds=6,
            total_icu_beds=10,
            occupied_icu_beds=4,
            avg_triage_time_min=6.0,
        ),
    ]


def _get_large_additions() -> list[Hospital]:
    """Thirteen further real Bangalore hospitals completing the large dataset.

    NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
    They are not real-world verified data. Do not cite as factual.
    """
    # ------------------------------------------------------------------
    # SIMULATION CONFIGURATION: every numeric capacity value below is
    # synthetic. Names and coordinates reference real institutions.
    #
    # Note: Fortis Hospital Bannerghatta Road (~12.8941, 77.5979) is
    # intentionally omitted here because that corridor is already
    # represented in the small dataset by Apollo Hospital Bannerghatta.
    # ------------------------------------------------------------------
    return [
        _build_hospital(
            hospital_id="vani_vilas",
            name="Vani Vilas Hospital (Vanivilas Women & Children)",
            latitude=12.9548,
            longitude=77.5832,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.PEDIATRIC_ICU,
            ],
            total_er_beds=40,
            occupied_er_beds=18,
            total_icu_beds=25,
            occupied_icu_beds=12,
            avg_triage_time_min=11.0,
        ),
        _build_hospital(
            hospital_id="hal_hospital",
            name="Hindustan Aeronautics Ltd Hospital",
            latitude=12.9608,
            longitude=77.6632,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=25,
            occupied_er_beds=10,
            total_icu_beds=12,
            occupied_icu_beds=5,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="sapthagiri",
            name="Sapthagiri Institute of Medical Sciences & Research Centre",
            latitude=13.0273,
            longitude=77.5720,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=45,
            occupied_er_beds=20,
            total_icu_beds=30,
            occupied_icu_beds=14,
            avg_triage_time_min=11.0,
        ),
        _build_hospital(
            hospital_id="fortis_cunningham",
            name="Fortis Hospital Cunningham Road",
            latitude=12.9985,
            longitude=77.5937,
            specialties=[
                HospitalSpecialty.CARDIAC_CATH_LAB,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=25,
            occupied_er_beds=11,
            total_icu_beds=16,
            occupied_icu_beds=7,
            avg_triage_time_min=7.0,
        ),
        _build_hospital(
            hospital_id="mallya",
            name="Mallya Hospital",
            latitude=12.9712,
            longitude=77.5988,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=30,
            occupied_er_beds=14,
            total_icu_beds=18,
            occupied_icu_beds=9,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="sakra_world",
            name="Sakra World Hospital",
            latitude=12.9352,
            longitude=77.6873,
            specialties=[
                HospitalSpecialty.LEVEL_1_TRAUMA,
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.STROKE_COMPREHENSIVE,
            ],
            total_er_beds=35,
            occupied_er_beds=15,
            total_icu_beds=22,
            occupied_icu_beds=10,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="baptist_hebbal",
            name="Baptist Hospital Hebbal",
            latitude=13.0398,
            longitude=77.5916,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=30,
            occupied_er_beds=12,
            total_icu_beds=16,
            occupied_icu_beds=7,
            avg_triage_time_min=9.0,
        ),
        _build_hospital(
            hospital_id="kims_vvpuram",
            name="Kempegowda Institute of Medical Sciences (KIMS) Hospital",
            latitude=12.9614,
            longitude=77.5735,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=50,
            occupied_er_beds=24,
            total_icu_beds=30,
            occupied_icu_beds=15,
            avg_triage_time_min=11.0,
        ),
        _build_hospital(
            hospital_id="esic_rajajinagar",
            name="ESIC Model & Super Speciality Hospital Rajajinagar",
            latitude=12.9968,
            longitude=77.5548,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=35,
            occupied_er_beds=15,
            total_icu_beds=20,
            occupied_icu_beds=9,
            avg_triage_time_min=10.0,
        ),
        _build_hospital(
            hospital_id="aster_rv_jpnagar",
            name="Aster RV Hospital JP Nagar",
            latitude=12.9063,
            longitude=77.5857,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.CARDIAC_CATH_LAB,
            ],
            total_er_beds=30,
            occupied_er_beds=13,
            total_icu_beds=20,
            occupied_icu_beds=9,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="columbia_asia_whitefield",
            name="Columbia Asia Hospital Whitefield",
            latitude=12.9645,
            longitude=77.7172,
            specialties=[
                HospitalSpecialty.GENERAL_EMERGENCY,
                HospitalSpecialty.LEVEL_2_TRAUMA,
            ],
            total_er_beds=28,
            occupied_er_beds=12,
            total_icu_beds=16,
            occupied_icu_beds=7,
            avg_triage_time_min=8.0,
        ),
        _build_hospital(
            hospital_id="sparsh_yeshwanthpur",
            name="Sparsh Hospital Yeshwanthpur",
            latitude=13.0225,
            longitude=77.5520,
            specialties=[
                HospitalSpecialty.LEVEL_2_TRAUMA,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=25,
            occupied_er_beds=11,
            total_icu_beds=15,
            occupied_icu_beds=7,
            avg_triage_time_min=7.0,
        ),
        _build_hospital(
            hospital_id="cloudnine_jayanagar",
            name="Cloudnine Hospital Jayanagar",
            latitude=12.9300,
            longitude=77.5838,
            specialties=[
                HospitalSpecialty.PEDIATRIC_ICU,
                HospitalSpecialty.GENERAL_EMERGENCY,
            ],
            total_er_beds=15,
            occupied_er_beds=6,
            total_icu_beds=12,
            occupied_icu_beds=5,
            avg_triage_time_min=6.0,
        ),
    ]


class BangaloreHospitalDataset:
    """Curated Bangalore hospital datasets at three scales.

    Geographic identity (names, coordinates) references real institutions;
    all operational capacity is synthetic.

    NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
    They are not real-world verified data. Do not cite as factual.
    """

    @classmethod
    def get_hospitals(cls, scale: str = "small") -> list[Hospital]:
        """Return the hospital roster for the requested scale.

        NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
        They are not real-world verified data. Do not cite as factual.

        Scales:
            "small":  6 hospitals  (the pre-existing default roster).
            "medium": 15 hospitals (small + 9 additional real sites).
            "large":  28 hospitals (medium + 13 additional real sites).

        Args:
            scale: One of "small", "medium", or "large".

        Returns:
            Freshly constructed Hospital instances (safe to mutate).

        Raises:
            ValueError: If ``scale`` is not a recognized option.
        """
        normalized = scale.strip().lower()
        if normalized == _SCALE_SMALL:
            return cls._get_small()
        if normalized == _SCALE_MEDIUM:
            return cls._get_medium()
        if normalized == _SCALE_LARGE:
            return cls._get_large()
        raise ValueError(
            f"Unknown hospital dataset scale {scale!r}. "
            f"Expected one of {_VALID_SCALES}."
        )

    @classmethod
    def _get_small(cls) -> list[Hospital]:
        """NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
        They are not real-world verified data. Do not cite as factual."""
        return get_default_bangalore_hospitals()

    @classmethod
    def _get_medium(cls) -> list[Hospital]:
        """NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
        They are not real-world verified data. Do not cite as factual."""
        return cls._get_small() + _get_medium_additions()

    @classmethod
    def _get_large(cls) -> list[Hospital]:
        """NOTE: Capacity numbers (beds, ICU) are SIMULATION CONFIGURATION.
        They are not real-world verified data. Do not cite as factual."""
        return cls._get_medium() + _get_large_additions()


def get_hospital_by_node_id(hospitals: list[Hospital], node_id: str) -> Hospital | None:
    """Find a hospital whose road-network node matches ``node_id``.

    Args:
        hospitals: Candidate hospital instances to search.
        node_id: Road-graph node identifier (e.g. "node_nimhans_hosp").

    Returns:
        The matching Hospital, or None if no hospital occupies that node.
    """
    for hospital in hospitals:
        if hospital.node_id == node_id:
            return hospital
    return None


def get_all_hospital_locations() -> list[tuple[str, float, float]]:
    """Return (name, latitude, longitude) for every known hospital.

    Aggregates all three scales (small, medium, large) regardless of which
    scale an individual simulation run uses, de-duplicated by hospital id.

    Coordinates are real-world approximations; no capacity data is exposed
    by this utility.

    Returns:
        List of (name, latitude, longitude) tuples.
    """
    seen_ids: set[str] = set()
    locations: list[tuple[str, float, float]] = []
    for hospital in (
        BangaloreHospitalDataset._get_small()
        + _get_medium_additions()
        + _get_large_additions()
    ):
        if hospital.id in seen_ids:
            continue
        seen_ids.add(hospital.id)
        locations.append((hospital.name, hospital.latitude, hospital.longitude))
    return locations
