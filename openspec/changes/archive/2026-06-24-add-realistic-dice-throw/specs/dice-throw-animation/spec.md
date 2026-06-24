## ADDED Requirements

### Requirement: Thrown-arc roll choreography

When the player activates the die, the system SHALL animate the roll as a thrown die rather than an in-place spin. The die SHALL launch into the frame, travel along a parabolic arc, tumble in flight, bounce twice with decaying vertical energy, and come to rest aligned to the server-rolled face. The animation is presentation only and SHALL NOT determine the outcome.

#### Scenario: Die follows a thrown arc

- **WHEN** the player activates the die for a resolved check
- **THEN** the die launches, travels along a parabolic arc while tumbling, and bounces before settling
- **AND** it does not merely spin in place around a fixed center

#### Scenario: Die bounces with decaying energy

- **WHEN** the die descends during the throw
- **THEN** it bounces twice, each bounce reaching a lower apex than the previous one
- **AND** it comes to rest after the final bounce

### Requirement: Deterministic landing on the server face

The thrown-arc animation SHALL always settle on the face matching the server-rolled d20 value. The trajectory and spin SHALL be scripted/eased (not a physics simulation), so the resting face is guaranteed regardless of the randomized in-flight motion. The displayed face, modifier, total, and result tier SHALL always equal the authoritative server result.

#### Scenario: Die lands on the server value

- **WHEN** the server-rolled value is 14 and the player activates the die
- **THEN** the die comes to rest showing face 14
- **AND** the revealed value, modifier, total, and result tier match the server result exactly

#### Scenario: Landing is guaranteed across repeated rolls

- **WHEN** the same value is rolled in separate checks with different randomized in-flight tumbles
- **THEN** the die settles on that value's face every time

### Requirement: Continuous deceleration without snapping

The die's orientation SHALL be integrated continuously throughout the throw and SHALL decelerate smoothly into the target face. The animation SHALL NOT teleport the die to an intermediate pose between the flight and the settle; the transition from tumbling to resting SHALL be continuous.

#### Scenario: No visible snap before settling

- **WHEN** the die transitions from in-flight tumbling to coming to rest
- **THEN** its orientation changes continuously with no instantaneous jump to a different pose

### Requirement: Camera framing for the arc

To fit the thrown arc within the canvas, the camera SHALL dolly back during the flight so the die reads as thrown from a distance, and SHALL dolly in as the die settles so the resting face is clearly legible. The die SHALL remain within the visible frame throughout the animation.

#### Scenario: Die stays within frame during flight

- **WHEN** the throw plays its arc
- **THEN** the die remains fully visible within the canvas at every point of the trajectory

#### Scenario: Resting face is clearly framed

- **WHEN** the die has settled
- **THEN** the camera is framed close enough that the resting face's number is clearly legible

### Requirement: Landing feedback

On each bounce impact the system SHALL apply a brief squash/stretch deformation to convey impact, and on final rest the existing critical-result emissive emphasis SHALL be applied for `exito_critico` and `fracaso_critico`. The settle SHALL invoke the settled callback exactly once.

#### Scenario: Impact deformation on bounce

- **WHEN** the die strikes the surface on a bounce
- **THEN** a brief squash/stretch deformation is shown for that impact

#### Scenario: Critical results emphasized on rest

- **WHEN** the die settles and the result tier is `exito_critico` or `fracaso_critico`
- **THEN** the resting die is visually emphasized distinctly from an ordinary success or failure

#### Scenario: Settled callback fires once

- **WHEN** the die finishes the throw and comes to rest
- **THEN** the settled callback is invoked exactly one time

### Requirement: Animation plays regardless of reduced motion

Activating the die SHALL always play the full thrown-arc animation, including when the environment requests reduced motion. The throw SHALL NOT be shortened or bypassed based on a reduced-motion preference.

#### Scenario: Throw plays under reduced motion

- **WHEN** the environment requests reduced motion and the player activates the die
- **THEN** the full thrown-arc animation plays

### Requirement: Graceful fallback without 3D rendering

When the 3D rendering context is unavailable, the system SHALL skip the animation and reveal the authoritative result directly, invoking the settled callback so the resolution still proceeds.

#### Scenario: WebGL unavailable

- **WHEN** a WebGL rendering context cannot be created
- **THEN** the animation is skipped and the settled callback is invoked so the result is revealed
