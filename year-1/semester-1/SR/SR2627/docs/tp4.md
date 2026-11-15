# TP4 - Programmable Firewall and Attack Monitoring Assignment

> Universidade do Minho
> MSc in Cybersecurity, Network Security, 2026/2027
> Source: `TP4 - Firewall.pdf` (4 pages)

## 1. Project Overview

Build a programmable firewall in Python or C and demonstrate that it can detect and respond to the network
attacks studied in class. Your system may run in the SEED Ubuntu 20.04 virtual machine or inside a
container-based lab. You may choose the supporting stack, but the firewall decision logic and the
attack-specific detection logic must be your own implementation.

The behavior of the firewall should be observable so that users have a history of attacks and what measures
were (or were not) taken by your implementation.

## 2. Learning Objectives

By the end of this project, students will be able to:

- translate observed attack behavior into concrete firewall and detection rules
- automate defenses against previously deployed attacks
- collect structured telemetry and present network behavior over time
- evaluate detection quality, mitigation effectiveness, and effects on legitimate traffic

## 3. Project Requirements

**Minimum attack coverage.** Implement detection capabilities and a defensive response for every attack or
attack scenario used in class. Optional attacks may extend the project, but they do not replace any required
class attack.

- **Student-written decisions.** Your code must decide when traffic is allowed, dropped, rejected, rate
  limited, or otherwise contained. Additional actions may be employed as you see fit.
- **Documented policy.** Define the default policy, allowed services, protected assets, exceptions, and the
  reason for each attack-specific response.
- **Attack detection.** For each attack, identify observable indicators and implement a detector that records
  why it fired. Use state, rolling counters, connection history, or timing windows when the defense requires
  context across packets.
- **Attack response.** Apply a response intended to stop or mitigate the attack. The response may include
  dropping packets, rejecting connections, rate limiting, temporary blocking, or another justified control.
- **Legitimate service.** Show that expected benign traffic still reaches the protected service before,
  during, and after each test. Measure and discuss false positives. Examples of services may include an HTTP
  server, SQL Database, etc.
- **Monitoring.** Record structured events and provide a view over time that correlates traffic, detections,
  enforcement actions, and test outcomes. You may create your own, but usage of at least some industry
  solutions is recommended.

## 4. Lab Setup and System Design

Submit an original topology diagram that matches the deployed system. The diagram must make the firewall's
position and the flow of traffic unambiguous.

### 4.1 Required Topology Content

- Every attacker, legitimate client, firewall, protected service, monitoring component, and management
  component.
- Trust zones, networks, subnets, IP addresses, interfaces, bridges, and exposed service ports used in the
  demonstration.
- The direction of normal and attack traffic, including the exact interception or enforcement point.
- The telemetry path from the firewall to logs, metrics storage, dashboards, or reports.
- Any traffic that bypasses the firewall and the reason it is out of scope.

### 4.2 Topology Skeleton

```text
[Attacker]     --->    [Firewall host] ---> [Protected service]
                             |
                             +---> [Telemetry store and time view]
```

Adapt this skeleton to your specific needs. Replace each label with actual components, addresses,
interfaces, packet paths, and telemetry paths. More complex designs may include multiple networks.

### 4.3 Design Explanation

- **Packet path.** Explain how a packet reaches your code, how the decision is made, and where the decision is
  enforced.
- **Detection model.** For each attack, describe the indicators, state or observation window, thresholds or
  logic, and conditions that clear the alert.
- **Policy model.** Explain the default behavior, allow rules, deny rules, temporary controls, and how
  conflicting decisions are resolved.
- **Telemetry model.** Explain which events and metrics are emitted, where they are stored, and how they are
  correlated with an experiment.
- **Failure behavior.** State what happens when the firewall process, log destination, or dashboard is
  unavailable, and describe how you recover safely.

### 4.4 Threat Model and Scope

Identify the assets being protected, the attacker capabilities assumed in the lab, the attacks addressed, and
important limitations. State which encrypted, fragmented, spoofed, distributed, or application-layer traffic
your design can and cannot inspect.

## 5. Attack Coverage and Test Method

Build a traceability matrix before implementation. Every required class attack must connect to a detector, a
response, a measurable success condition, and final evidence. Use the attack names and terminology from the
class material.

| Attack scenario | Observable indicator | Firewall response | Success measure |
| --- | --- | --- | --- |
| [Attack 1] | [Packets, rate, state, sequence, signature, or behavior] | [Drop, reject, limit, block, or other control] | [What proves the attack stopped or was reduced] |
| [Attack 2] | [Packets, rate, state, sequence, signature, or behavior] | [Drop, reject, limit, block, or other control] | [What proves the attack stopped or was reduced] |
| … | … | … | … |

### 5.1 Required Procedure for Each Attack

1. **Define the expected result.** State the protected service, the attack objective, the detector trigger,
   the intended firewall action, and the success metric before running the test.
2. **Establish a benign baseline.** Generate legitimate traffic and record availability, traffic rate,
   latency or another relevant service measure, and any alerts. Assessing whether your system is working as
   intended should be the first step before you implement any of the attacks / attempt to mitigate them.
3. **Measure the unmitigated condition.** When it is safe in the isolated lab, show the attack effect with the
   attack-specific defense disabled. Keep baseline safety controls in place.
4. **Enable the defense.** Run the same attack with both firewall and monitoring active. Use comparable
   duration, intensity, and target conditions.
5. **Correlate evidence.** Record the attack start, detection time, enforcement time, firewall action, and end
   of the attack window using synchronized timestamps.
6. **Verify the outcome.** Show whether the attack succeeded, was reduced, or was stopped, and confirm whether
   legitimate use continued.
7. **Repeat and interpret.** Run enough trials to show that the result is reproducible. Explain variability,
   false positives, false negatives, and limitations.

### 5.2 Result Categories

| Result | Meaning |
| --- | --- |
| Stopped | The attack objective was not achieved under the stated success measure, and the evidence shows that the firewall response caused the result. |
| Reduced | The defense measurably limited the attack but did not prevent the objective completely. |
| Detected only | The detector produced a valid alert, but the response did not materially reduce the attack. |
| Not detected | The attack occurred without a valid detector event. Explain the gap and a credible next change. |

## 6. Monitoring and Visibility

The monitoring view is a required part of the firewall. It must show what happened over time, when the system
detected an attack, which measures it applied, and whether those actions were effective. A terminal that
displays only the latest message is not sufficient.

Along with the time-based view below, you should monitor which services are up or down in your environment at
all times.

### 6.1 Required Time-based View

- An entry for each event with information on which attack was detected.
- Traffic volume or event rate, with allowed and blocked or limited traffic distinguishable.
- Detection events labeled by attack type or detector, with severity or confidence when used.
- Enforcement actions labeled separately from detections so the marker can see whether action followed an
  alert.
- A clear outcome for each trial: stopped, reduced, detected only, or not detected.

### 6.2 Minimum Event Record

| Field | Required content | Purpose |
| --- | --- | --- |
| Time | Timestamp with stated timezone and sufficient precision | Correlate attack, detection, and response |
| Attack | Attack label | Separate trials and connect evidence |
| Traffic | Source, destination, protocol, ports, interface, and direction when available | Identify the affected flow |
| Decision | Allow, drop, reject, limit, temporary block, or other action | Show what the firewall enforced |
| Reason | Rule, detector, threshold, signature, or state that caused the decision | Make the decision explainable |
| Counters | Relevant packet, byte, flow, rate, or state values | Support the detection claim |
| Outcome | Stopped, reduced, detected only, not detected, or benign | Record the evaluated result |

If a defense does not stop an attack, label the outcome accurately and explain why. Clear instrumentation and
analysis can earn credit for the experimental method, but full effectiveness credit requires a reproducible
mitigation.

## 7. Presentation

Demonstrate the system live and be ready to answer questions regarding your implementation, architecture, and
the code that has been produced.

Code you cannot justify or explain will invalidate that part of your project.

There will be a graded checkpoint before the final presentation.

## 8. Code, Report and Submission

Prepare the code for reproducibility, ensuring:

- **Deployment materials:** Code, scripts, rules, container files, orchestration files, or VM setup commands
  needed to reproduce your environment.
- **README:** Exact commands to start the topology, firewall, monitoring, benign traffic, and each attack test.

The report must address:

- **Architecture and security design:** network topology, firewall placement and role, packet path, threat
  model, and filtering policy.
- **Software structure and execution:** main modules and their responsibilities, execution model (including
  processes or threads, where applicable), communication and synchronisation between components, and system
  initialisation, configuration, and shutdown.
- **Automatic attack detection and response:** traffic information collected, detection criteria and
  parameters, and how detection triggers alerts or filtering changes. Include an attack traceability matrix
  linking each required attack to its detection mechanism, response, and validation tests.
- **Testing and results:** test scenarios and methodology covering both attack and legitimate traffic,
  supported by clearly referenced evidence such as structured logs, monitoring exports, graphs, or dashboard
  captures.
- **Critical analysis and conclusions:** justification of the main design decisions, interpretation of results,
  false positives and false negatives, mitigation effectiveness, and operational limitations.
- **Individual contributions:** for team submissions, identify each member's technical and documentation
  contributions.
- **Declaration of AI use and responsibility:** identify the tools and model versions used, summarise relevant
  prompts and responses, explain their application to the work and how outputs were validated. Include a
  statement confirming responsibility for and understanding of the submitted code and content. If no AI tools
  were used, state this explicitly.
- Use diagram and selected pseudocode where helpful to explain the solution; avoid extensive source code
  listings.
- **Final submission:** complete the submission through the BlackBoard Assignment hand-in. Each working group
  should upload a single `.zip` file containing the report and code files. It should follow this naming scheme:
  `NS-TP4-PL1x.zip`, `x` is the working group.

## 9. Safety and Authorization

- Run attacks only in the isolated SEED VM or container lab authorized for this course. Do not direct attack
  traffic at university production systems, public services, home networks, or systems owned by another
  person.
- Capture only the traffic needed for the experiment. Remove credentials and unrelated personal data from logs,
  packet captures, screenshots, and repositories.
- Do not weaken host security or expose the lab to external networks for convenience. Document any elevated
  container capabilities or root privileges and limit them to the lab components that require them.

## 10. Important Dates

- **Checkpoint:** 10.12.2026, 14h-16h – make sure to prepare a ~10 minute presentation where you go through
  your proposed architecture, the state of your project, and next steps.
- **Code+Report Submission:** 10.01.2027, 23h59
- **Presentation (demonstration):** 14.01.2027, schedule to be defined
