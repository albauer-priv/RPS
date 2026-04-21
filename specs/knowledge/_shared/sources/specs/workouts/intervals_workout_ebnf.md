---
Type: Specification
Specification-For: WORKOUT_GRAMMAR
Specification-ID: IntervalsWorkoutEBNF
Version: 1.0

Scope: Shared
Authority: Binding

Normative-Role: StructuralRules
Decision-Authority: None

Applies-To:
  - Workout Export
  - Week-Planner

Notes: >
  Defines the formal EBNF grammar for Intervals.icu-compatible workout text.
  This specification governs syntax, structure, and valid tokens for parsing,
  validation, and export. It defines no training intent, thresholds, or
  planning decisions and must not be interpreted as a workout prescription.
---




(*
  Intervals.icu workout text – merged EBNF
  - No nested loops
  - First paragraph becomes description
  - Category:, loops, sections, steps, text events, flags, device mods
*)

(* ========== 1. Top-level document structure ========== *)

<workout> ::= { <paragraph> } <block-list>

(* First paragraph(s) before blocks become workout description *)

<paragraph> ::= <non-empty-line> { <non-empty-line> } <blank-line>

<block-list> ::= { <block> | <blank-line> }+

<block> ::= <loop-block>
          | <section-block>
          | <standalone-step>
          | <category-line>

(* Loop: header with Nx followed by steps; no nested loops *)

<loop-block> ::= <loop-header> <blank-or-eof> <step-list>

<loop-header> ::= <header-text> <ws> <repeat-count>
                | <repeat-count-only>

<repeat-count-only> ::= <repeat-count>

<repeat-count> ::= <integer> ( "x" | "X" )
(* e.g. "Main set 6x", "3x" *)

(* Section: header without repeat count, followed by steps *)

<section-block> ::= <section-header> <blank-or-eof> <step-list>

<section-header> ::= <header-text> <blank-or-eof>
(* e.g. "Warmup", "Cooldown", "Main Set" *)

<standalone-step> ::= <step-line>

(* Steps under a loop or section, with blank lines allowed *)

<step-list> ::= <step-line> { <blank-line> | <step-line> }

(* Category line controls Zwift folder/category *)

<category-line> ::= "Category:" <ws> <header-text> <blank-or-eof>


(* ========== 2. Lines, whitespace, tokens ========== *)

<step-line> ::= "-" <ws-opt> <step-body> <blank-or-eof>

<header-text> ::= <text-fragment> { <ws> <text-fragment> }

<text-fragment> ::= <word> | <symbol-sequence>

<word> ::= <letter-or-digit> { <letter-or-digit> | "_" | "/" | "'" }

<symbol-sequence> ::= <non-space-non-newline-char>
                      { <non-space-non-newline-char> }

<blank-line> ::= <ws-opt> <newline>

<blank-or-eof> ::= <ws-opt> ( <newline> | EOF )

<ws> ::= ( " " | "\t" ) { " " | "\t" }

<ws-opt> ::= | <ws>

<non-empty-line> ::= (not <newline> and not EOF)* <newline>

(* Character classes – abstracted; implementation-specific *)

<letter-or-digit> ::= <letter> | <digit>

<letter> ::= "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J"
           | "K" | "L" | "M" | "N" | "O" | "P" | "Q" | "R" | "S" | "T"
           | "U" | "V" | "W" | "X" | "Y" | "Z"
           | "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j"
           | "k" | "l" | "m" | "n" | "o" | "p" | "q" | "r" | "s" | "t"
           | "u" | "v" | "w" | "x" | "y" | "z"

<digit> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"

<non-space-non-newline-char> ::= (* any char except " " and newline *)

<newline> ::= "\n"  (* or environment-specific newline *)

<integer> ::= <digit> { <digit> }

<number> ::= <integer> [ "." <integer> ]


(* ========== 3. Step structure ========== *)

(* Conceptual pattern:
   - [labels / text events] [duration] [targets] [cadence] [flags]
*)

<step-body> ::= [ <step-text-and-text-events> <ws> ]
                [ <duration> <ws-opt> ]
                [ <target-list> <ws-opt> ]
                [ <cadence> <ws-opt> ]
                [ <step-flags> ]

(* Everything before the first recognised duration or target token
   is treated as label + optional timed text events.
*)

<step-text-and-text-events> ::= <text-events>
                              | <label-text>
                              | <label-text> <ws> <text-events>

<label-text> ::= <text-token> { <ws> <text-token> }

<text-token> ::= <word> | <symbol-sequence>

<target-list> ::= <target> { <ws> <target> }



(* ========== 4. Duration ========== *)

<duration> ::= <time-duration> | <distance-duration>

(* 4.1 Time-based durations *)

<time-duration> ::= <time-number> <time-unit>
                  | <minute-second-combo>
                  | <hour-minute-combo>

<time-number> ::= <number>

<time-unit> ::= "s"
              | "\""
              | "m"
              | "'"
              | "h"
              | "hour"
              | "hours"

(* e.g. "1m30" for 1:30 *)
<minute-second-combo> ::= <integer> "m" <integer>

(* e.g. "2h35m" for 2:35:00 *)
<hour-minute-combo> ::= <integer> "h" <integer> "m"

(* 4.2 Distance-based durations *)

<distance-duration> ::= <distance-number> <ws-opt> <distance-unit>

<distance-number> ::= <number>

<distance-unit> ::= "km"
                  | "mi"
                  | "mile"
                  | "miles"
                  | "mtr"
                  | "meters"
                  | "yrd"
                  | "yards"
                  | "y"

(* ========== 5. Targets (power, HR, pace, zones, ramp, freeride) ========== *)

<target> ::= <power-target>
           | <hr-target>
           | <pace-target>
           | <zone-target>
           | <ramp-target>
           | <freeride-target>


(* 5.1 Power *)

<power-target> ::= <power-absolute>
                 | <power-percent>
                 | <power-range>

<power-absolute> ::= <number> "w" | <number> "W"

<power-percent> ::= <number> "%"

<power-range> ::= <number> "-" <number> "%"
                | <number> "-" <number> ( "w" | "W" )

(* 5.2 Heart rate *)

<hr-target> ::= <number> "%" "HR"
              | <number> "%" "hr"
              | <number> "%" "LTHR"
              | <number> "%" "lthr"
              | <zone-token> <ws> ( "HR" | "hr" )

(* 5.3 Pace *)

<pace-target> ::= <pace-relative>
                | <pace-absolute>
                | <pace-absolute-range>

<pace-relative> ::= <number> "%" "Pace"
                  | <zone-token> <ws> "Pace"

<pace-absolute> ::= <pace-time> [ <pace-unit> ] <ws-opt> "Pace"

<pace-absolute-range> ::= <pace-time> "-" <pace-time>
                          [ <pace-unit> ] <ws-opt> "Pace"

<pace-time> ::= <integer> ":" <two-digit>   (* mm:ss *)

<two-digit> ::= <digit> <digit>

<pace-unit> ::= "/km"
              | "/mi"
              | "/100m"
              | "/500m"
              | "/100y"
              | "/400m"
              | "/250m"

(* 5.4 Zone shorthand *)

<zone-target> ::= <zone-token>
                | <zone-token> <ws> "HR"
                | <zone-token> <ws> "Pace"

<zone-token> ::= ( "Z" | "z" ) <integer>
(* Typically Z1–Z7 in practice *)

(* 5.5 Ramp *)

<ramp-target> ::= "ramp" <ws> <ramp-range> [ <ws> <ramp-basis> ]

<ramp-range> ::= <number> "-" <number> "%"
               | <number> "-" <number> ( "w" | "W" )

<ramp-basis> ::= "FTP"
               | "HR"
               | "LTHR"
               | "Pace"
               | "pace"
               | "MMP" <ws> <time-duration>
(* MMP basis is a merged extension; may or may not be used in all exports *)

(* 5.6 Freeride *)

<freeride-target> ::= "freeride" | "FreeRide"


(* ========== 6. Cadence ========== *)

<cadence> ::= <cadence-absolute> | <cadence-range>

<cadence-absolute> ::= <integer> "rpm"

<cadence-range> ::= <integer> "-" <integer> "rpm"


(* ========== 7. Flags and advanced tokens ========== *)

<step-flags> ::= <flag-token> { <ws> <flag-token> }

<flag-token> ::= <hidepower-flag>
               | <press-lap-flag>
               | <intensity-flag>
               | <device-target-mod>
               | <other-flag-token>

(* 7.1 hidepower / /hidepower — Zwift show_avg control *)

<hidepower-flag> ::= "hidepower" | "/hidepower"

(* 7.2 press lap – lap-button-controlled end *)

<press-lap-flag> ::= "press" <ws> "lap" [ <press-lap-trailer> ]

<press-lap-trailer> ::= { <ws> <text-token> }
(* e.g. "press lap when ready" *)

(* 7.3 FIT intensity flag *)

<intensity-flag> ::= "intensity=" <intensity-value>

<intensity-value> ::= "active"
                    | "recovery"
                    | "interval"
                    | "warmup"
                    | "cooldown"
                    | "rest"
                    | "other"
                    | "auto"
                    | <other-intensity-string>

<other-intensity-string> ::= <word>

(* 7.4 Device target modifiers (Garmin power/HR modes) *)

<device-target-mod> ::= "power=" <power-target-mode>
                      | "hr=" <hr-target-mode>

<power-target-mode> ::= "lap"
                      | "1s" | "3s" | "10s" | "30s"

<hr-target-mode> ::= "lap"
                   | "1s"

(* 7.5 Fallback for future flags *)

<other-flag-token> ::= <text-token>


(* ========== 8. Text events (Zwift prompts) ========== *)

(* Timed text events live before duration/targets in the step text *)

<text-events> ::= <text-event> { <ws> <text-event> }

<text-event> ::= [ <event-message-prefix> <ws> ]
                 <timeoffset> "^" [ <duration-seconds> ]
                 [ <ws> <event-message> ]

<timeoffset> ::= <integer>          (* seconds from step start *)
<duration-seconds> ::= <integer>    (* seconds message is visible *)

<event-message-prefix> ::= <label-text>
<event-message> ::= <label-text>
