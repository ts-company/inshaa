import math
import os
import unittest
from datetime import date, datetime

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.routes.project_dashboard import (
    _calendar_prefix,
    _parse_xer_calendar,
    _planned_progress,
    _rebuild_baseline_schedule,
    build_dashboard_data,
    parse_xer,
)


class BuildDashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.xer_data = {
            "header": {"export_date": "2026-11-05"},
            "tables": {
                "PROJWBS": [
                    {
                        "wbs_id": "1",
                        "parent_wbs_id": "",
                        "wbs_name": "PK13-E",
                        "proj_node_flag": "Y",
                    },
                    {
                        "wbs_id": "2",
                        "parent_wbs_id": "1",
                        "wbs_name": "Group 1",
                        "seq_num": "1",
                    },
                    {
                        "wbs_id": "3",
                        "parent_wbs_id": "2",
                        "wbs_name": "Villa 21 Left",
                        "seq_num": "1",
                    },
                ],
                "TASK": [
                    {
                        "task_id": "101",
                        "wbs_id": "3",
                        "task_name": "Interior Painting",
                        "target_cost": "100",
                        "phys_complete_pct": "50",
                        "target_start_date": "2026-11-01",
                        "target_end_date": "2026-11-10",
                        "early_end_date": "2026-11-12",
                    },
                    {
                        "task_id": "102",
                        "wbs_id": "3",
                        "task_name": "Floor Ceramic Tiles",
                        "target_cost": "",
                        "phys_complete_pct": "0.3",
                        "target_start_date": "2026-11-01",
                        "target_end_date": "2026-11-20",
                    },
                    {
                        "task_id": "103",
                        "wbs_id": "2",
                        "task_name": "Procurement Delivery",
                        "target_cost": "100",
                        "phys_complete_pct": "50",
                        "target_start_date": "2026-11-01",
                        "target_end_date": "2026-11-20",
                    },
                ],
                "TASKRSRC": [
                    {"task_id": "102", "target_cost": "200"},
                ],
            },
        }

    def test_converts_xer_tables_to_chart_payload(self):
        payload = build_dashboard_data(self.xer_data)

        self.assertEqual(payload["t"], {"b": 400.0, "p": 107.6, "e": 160.0})
        self.assertEqual(payload["cs"]["b"], 300.0)
        self.assertEqual(payload["pr"]["b"], 100.0)
        self.assertEqual(len(payload["gr"]), 4)
        self.assertEqual(payload["gr"][0]["c"]["b"], 300.0)
        self.assertEqual(payload["v"][0]["n"], "Villa 21 Left")
        self.assertEqual(payload["v"][0]["it"]["P"][0], ["Interior Painting", 100.0, 50.0])
        self.assertEqual(
            payload["v"][0]["it"]["F"][0],
            ["Ceramic · Bathroom floors", 200.0, 60.0],
        )

    def test_flooring_excludes_activities_that_only_mention_a_floor_location(self):
        task_names = (
            "Install of Wiring Devices For First Floor",
            "Floor Plumping First Fix Works",
            "Air Grilles Installation For Ground Floor",
            "Marble Countertop For Bathroom",
        )
        self.xer_data["tables"]["TASK"].extend(
            {
                "task_id": str(104 + index),
                "wbs_id": "3",
                "task_name": name,
                "target_cost": "50",
                "phys_complete_pct": "0.5",
            }
            for index, name in enumerate(task_names)
        )

        payload = build_dashboard_data(self.xer_data)
        villa = payload["v"][0]
        flooring_trade = next(
            trade for trade in villa["tr"] if trade[0] == "Flooring, Tiles & Marble"
        )

        self.assertEqual(flooring_trade[6], 200.0)
        self.assertEqual(payload["itn"]["F"], ["Ceramic · Bathroom floors"])
        self.assertEqual(
            villa["it"]["F"],
            [["Ceramic · Bathroom floors", 200.0, 60.0]],
        )

    def test_group_level_construction_stays_out_of_villa_totals(self):
        self.xer_data["tables"]["TASK"].append(
            {
                "task_id": "104",
                "wbs_id": "2",
                "task_name": "Common Area Painting",
                "target_cost": "50",
                "phys_complete_pct": "50",
                "target_start_date": "2026-11-01",
                "target_end_date": "2026-11-20",
            }
        )

        payload = build_dashboard_data(self.xer_data)

        self.assertEqual(payload["t"]["b"], 450.0)
        self.assertEqual(len(payload["v"]), 1)
        self.assertEqual(payload["v"][0]["b"], 300.0)
        self.assertNotEqual(payload["v"][0]["n"], "Project works")

    def test_trade_status_distinguishes_active_from_waiting_work(self):
        tasks = self.xer_data["tables"]["TASK"]
        tasks[0]["status_code"] = "TK_Active"
        tasks[1]["status_code"] = "TK_NotStart"

        payload = build_dashboard_data(self.xer_data)
        trade_status = {trade[0]: trade[2] for trade in payload["v"][0]["tr"]}

        self.assertEqual(trade_status["Painting"], "In Progress")
        self.assertEqual(trade_status["Flooring, Tiles & Marble"], "Waiting")

    def test_duration_complete_progress_uses_remaining_duration(self):
        task = {
            "complete_pct_type": "CP_Drtn",
            "phys_complete_pct": "0",
            "target_drtn_hr_cnt": "24",
            "remain_drtn_hr_cnt": "15.6",
        }

        payload = build_dashboard_data(
            {
                "header": {"export_date": "2026-11-05"},
                "tables": {
                    "PROJWBS": self.xer_data["tables"]["PROJWBS"],
                    "TASK": [
                        {
                            **task,
                            "task_id": "101",
                            "wbs_id": "3",
                            "task_name": "Interior Painting",
                            "target_cost": "100",
                            "target_start_date": "2026-11-01",
                            "target_end_date": "2026-11-10",
                        }
                    ],
                    "TASKRSRC": [],
                },
            }
        )

        self.assertEqual(payload["v"][0]["e"], 35.0)

    def test_chart_ready_data_replaces_non_finite_numbers(self):
        payload = {
            "t": {"b": float("nan"), "p": float("inf"), "e": 1},
            "cs": {"b": 1, "p": 1, "e": 1},
            "pr": {"b": 0, "p": 0, "e": 0},
            "gr": [],
            "MN": {},
            "BN": {},
            "v": [{"b": float("-inf")}],
            "itn": {},
        }

        result = build_dashboard_data(payload)

        self.assertEqual(result["t"], {"b": 0.0, "p": 0.0, "e": 1})
        self.assertTrue(math.isfinite(result["t"]["b"]))
        self.assertTrue(math.isfinite(result["t"]["p"]))
        self.assertEqual(result["cs"], payload["cs"])
        self.assertEqual(result["v"], [{"b": 0.0}])

    def test_planned_progress_uses_xer_working_days(self):
        separator = "\x7f\x7f"
        calendar_data = separator.join(
            [
                "(0||CalendarData()(",
                "  (0||DaysOfWeek()(",
                "    (0||1()(",
                "      (0||0(s|08:00|f|16:00)())))",
                "    (0||2()())",
                "    (0||3()(",
                "      (0||0(s|08:00|f|16:00)())))",
                "    (0||4()())",
                "    (0||5()())",
                "    (0||6()())",
                "    (0||7()())))",
                "  (0||Exceptions()())",
            ]
        )
        calendar = _parse_xer_calendar(
            {"clndr_id": "test", "clndr_data": calendar_data}
        )
        prefix = _calendar_prefix(
            calendar,
            start=date(2026, 11, 1),
            finish=date(2026, 11, 4),
        )

        progress = _planned_progress(
            date(2026, 11, 1),
            date(2026, 11, 4),
            date(2026, 11, 3),
            fallback=0.0,
            working_hours=prefix,
        )

        self.assertEqual(progress, 0.5)

    def test_baseline_schedule_uses_original_durations_and_predecessor_lag_calendar(self):
        six_day_calendar = {
            "weekly": {
                day: ([(8 * 60, 16 * 60)] if day != 6 else [])
                for day in range(1, 8)
            },
            "exceptions": {},
        }
        seven_day_calendar = {
            "weekly": {
                day: [(8 * 60, 16 * 60)]
                for day in range(1, 8)
            },
            "exceptions": {},
        }
        schedule = _rebuild_baseline_schedule(
            {
                "TASKPRED": [
                    {
                        "pred_task_id": "1",
                        "task_id": "2",
                        "pred_type": "PR_FS",
                        "lag_hr_cnt": "8",
                    }
                ]
            },
            [
                {"task_id": "1", "clndr_id": "six", "target_drtn_hr_cnt": "8"},
                {"task_id": "2", "clndr_id": "seven", "target_drtn_hr_cnt": "8"},
            ],
            {"six": six_day_calendar, "seven": seven_day_calendar},
            {
                "clndr_id": "six",
                "plan_start_date": "2026-11-05 08:00",
            },
        )

        self.assertEqual(
            schedule["1"],
            (datetime(2026, 11, 5, 8), datetime(2026, 11, 5, 16)),
        )
        self.assertEqual(
            schedule["2"],
            (datetime(2026, 11, 8, 8), datetime(2026, 11, 8, 16)),
        )

    def test_baseline_planned_value_uses_project_data_date(self):
        separator = "\x7f\x7f"
        calendar_data = separator.join(
            [
                "(0||CalendarData()(",
                "  (0||DaysOfWeek()(",
                "    (0||1()())",
                "    (0||2()( (0||0(s|08:00|f|16:00)())))",
                "    (0||3()( (0||0(s|08:00|f|16:00)())))",
                "    (0||4()( (0||0(s|08:00|f|16:00)())))",
                "    (0||5()( (0||0(s|08:00|f|16:00)())))",
                "    (0||6()( (0||0(s|08:00|f|16:00)())))",
                "    (0||7()())))",
                "  (0||Exceptions()())",
            ]
        )
        data = {
            "header": {"export_date": "2027-01-01"},
            "tables": {
                "PROJECT": [
                    {
                        "clndr_id": "workweek",
                        "plan_start_date": "2026-11-02 08:00",
                        "last_recalc_date": "2026-11-03 08:00",
                    }
                ],
                "PROJWBS": self.xer_data["tables"]["PROJWBS"],
                "TASK": [
                    {
                        "task_id": "101",
                        "wbs_id": "3",
                        "task_name": "Interior Painting",
                        "target_drtn_hr_cnt": "16",
                        "clndr_id": "workweek",
                        "target_cost": "",
                        "phys_complete_pct": "0",
                        "target_start_date": "2026-12-01",
                        "target_end_date": "2026-12-02",
                    }
                ],
                "TASKRSRC": [{"task_id": "101", "target_cost": "100"}],
                "TASKPRED": [],
                "CALENDAR": [
                    {"clndr_id": "workweek", "clndr_data": calendar_data}
                ],
            },
        }

        payload = build_dashboard_data(data)

        self.assertEqual(payload["t"]["p"], 50.0)
        self.assertEqual(payload["v"][0]["bl"], "03-Nov-26")

    def test_xer_parser_preserves_unknown_and_empty_table_schemas(self):
        header_fields = [
            "24.12",
            "2026-11-05",
            "Project",
            "export-user",
            "company",
            "database",
            "product",
            "EGP",
            "extra-header-field",
        ]
        xer = "\n".join(
            [
                "ERMHDR\t" + "\t".join(header_fields),
                "%T\tPROJECT",
                "%F\tproj_id",
                "%R\t1",
                "%T\tPROJWBS",
                "%F\twbs_id\tproj_id\tproj_node_flag",
                "%R\t2\t1\tY",
                "%T\tTASK",
                "%F\ttask_id\ttask_name",
                "%R\t3\tActivity",
                "%T\tUNKNOWN_TABLE",
                "%F\tcustom_value\tempty_value",
                "%R\tCafé £…\t",
                "%T\tEMPTY_TABLE",
                "%F\tretained_column",
                "%E",
            ]
        ).encode("cp1252")

        header, tables = parse_xer(xer)

        self.assertEqual(header["raw_fields"], header_fields)
        self.assertEqual(header["table_fields"]["UNKNOWN_TABLE"], ["custom_value", "empty_value"])
        self.assertEqual(header["table_fields"]["EMPTY_TABLE"], ["retained_column"])
        self.assertEqual(tables["UNKNOWN_TABLE"], [{"custom_value": "Café £…", "empty_value": ""}])
        self.assertEqual(tables["EMPTY_TABLE"], [])


if __name__ == "__main__":
    unittest.main()
