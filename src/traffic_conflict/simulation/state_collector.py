"""Collecte par abonnements TraCI, avec attente physique mesurée en Python."""
from collections import defaultdict

import traci.constants as tc

from traffic_conflict.domain.models import VehicleState


class StateCollector:
    VARIABLES = (tc.VAR_POSITION, tc.VAR_SPEED, tc.VAR_LANE_ID, tc.VAR_ROAD_ID,
                 tc.VAR_ROUTE_ID, tc.VAR_WAITING_TIME, tc.VAR_ANGLE,
                 tc.VAR_LANEPOSITION, tc.VAR_LENGTH)

    def __init__(self, connection, config: dict):
        self.connection = connection
        self.config = config
        self.subscribed = set()
        self.lane_lengths = {}
        self.waiting = defaultdict(float)
        self.cumulative = defaultdict(float)

    def collect(self) -> dict[str, VehicleState]:
        conn = self.connection
        now = conn.simulation.getTime()
        active = set(conn.vehicle.getIDList())
        self.subscribed.intersection_update(active)
        for vehicle_id in sorted(active - self.subscribed):
            conn.vehicle.subscribe(vehicle_id, self.VARIABLES)
            self.subscribed.add(vehicle_id)
        observations = conn.vehicle.getAllSubscriptionResults()
        states = {}
        for vehicle_id in sorted(active):
            values = observations[vehicle_id]
            lane, road = values[tc.VAR_LANE_ID], values[tc.VAR_ROAD_ID]
            if lane not in self.lane_lengths:
                self.lane_lengths[lane] = conn.lane.getLength(lane)
            speed, position = values[tc.VAR_SPEED], values[tc.VAR_LANEPOSITION]
            stopped = speed < self.config["detection"]["stopped_speed"]
            dt = self.config["simulation"]["step_length"]
            self.waiting[vehicle_id] = self.waiting[vehicle_id] + dt if stopped else 0.0
            self.cumulative[vehicle_id] += dt if stopped else 0.0
            route_id = values[tc.VAR_ROUTE_ID]
            _, approach, movement = route_id.split("_", 2)
            x, y = values[tc.VAR_POSITION]
            distance = self.lane_lengths[lane] - position if road.endswith("_in") else -position if road.endswith("_out") else 0.0
            states[vehicle_id] = VehicleState(
                vehicle_id=vehicle_id, time=now, x=x, y=y, speed=speed,
                lane_id=lane, road_id=road, route_id=route_id,
                waiting_time=self.waiting[vehicle_id], cumulative_waiting_time=self.cumulative[vehicle_id],
                sumo_waiting_time=values[tc.VAR_WAITING_TIME], heading=values[tc.VAR_ANGLE],
                distance_to_junction=distance, is_stopped=stopped, approach=approach,
                movement=movement, length=values[tc.VAR_LENGTH], lane_position=position)
        return states
