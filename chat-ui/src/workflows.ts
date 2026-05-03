/**
 * Seven clinician-facing demo prompts aligned with deploy/CLINICIAN-WORKFLOWS.md.
 * Uses the baked Synthea CSV seed patient (Brekke496).
 */
export const DEMO_SEED_PATIENT_ID = "f1aa52b9-aded-3188-9386-012244805ebf";

export type WorkflowPreset = {
  id: string;
  title: string;
  role: "PHYSICIAN" | "CLINICIAN" | "ADMIN";
  prompt: string;
};

export const CLINICIAN_WORKFLOWS: readonly WorkflowPreset[] = [
  {
    id: "w1",
    title: "Chart snapshot",
    role: "PHYSICIAN",
    prompt:
      "Who is this patient? State full name, age from date of birth, sex, and city/state. Use tools only if needed.",
  },
  {
    id: "w2",
    title: "Active medications",
    role: "PHYSICIAN",
    prompt:
      "List active medications for this patient with approximate start dates. Call the appropriate tool.",
  },
  {
    id: "w3",
    title: "Laboratory review",
    role: "PHYSICIAN",
    prompt:
      "Summarize recent laboratory results; focus on abnormal patterns if any appear in the data.",
  },
  {
    id: "w4",
    title: "Vital signs",
    role: "PHYSICIAN",
    prompt:
      "What are the most recent vital signs available? Give values with units when present.",
  },
  {
    id: "w5",
    title: "Allergies",
    role: "PHYSICIAN",
    prompt:
      "List documented allergies or intolerances before I order new meds.",
  },
  {
    id: "w6",
    title: "Nurse chart pull (RBAC)",
    role: "CLINICIAN",
    prompt:
      "Pull demographics, vitals, and allergies in one turn. Do not access laboratory results.",
  },
  {
    id: "w7",
    title: "Admin scheduling (RBAC)",
    role: "ADMIN",
    prompt: "Give me this patient's name and city of residence for scheduling.",
  },
] as const;
