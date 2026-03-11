package dsl

#Pattern: "pipeline" | "gated_pipeline" | "autonomous_cluster" | "consensus"

#Meta: {
  id:          string
  name:        string
  version:     string
  pattern:     #Pattern
  description?: string
}

#Agent: {
  runtime_id:   string
  role?:        string
  instructions?: string
  timeout_sec?: int & >=1
  retries?:     int & >=1
}

#Transition: {
  decision: string
  to:       string
}

#Consensus: {
  voters:      [...string]
  algorithm:   "majority" | "weighted" | "unanimity"
  threshold?:  number & >=0 & <=1
  tie_breaker?: string
  weights?:    [string]: number & >0
}

#ClusterMember: {
  agent:    string
  role?:    string
  required?: bool
}

#Stage: {
  id:               string
  kind:             "initiator" | "planner" | "gate" | "executor" | "auditor" | "orchestrator" | "consensus" | "cluster" | "terminal"
  agent?:           string
  description?:     string
  prompt_template?: string
  default_decision?: string
  transitions?:     [...#Transition]
  consensus?:       #Consensus
  cluster_members?: [...#ClusterMember]
}

#Feature: {
  name:   string
  enabled?: bool
  config?: {}
}

#Policy: {
  banned_terms?:          [...string]
  require_json_decision?: bool
  max_steps?:             int & >=1
}

#Spec: {
  meta:        #Meta
  entry_stage: string
  agents:      [string]: #Agent
  stages:      [...#Stage]
  features?:   [...#Feature]
  policy?:     #Policy
}
