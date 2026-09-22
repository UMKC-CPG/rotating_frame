# Pseudocode 1: The Frame and the Transform

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. Implements Design 1. Governs
> `src/rotating_frame/core/frame.py` and its test,
> `tests/unit/test_frame.py`. *Status: draft.*

New code, not a graft: nothing in the skeleton is replaced by this
section, and nothing yet calls it. The names below are the names the
code uses. Arrays are NumPy arrays of `float64`; a "vector" is shape
`(3,)`, a "matrix" `(3, 3)`, and a function marked *vectorized*
accepts a leading sample axis, `(N, 3)` and `(N,)`, and returns the
same leading shape.

---

## 1.1 The module and its constants

```
module rotating_frame.core.frame

IDENTITY = 3 × 3 identity matrix
```

No other constant. The module imports NumPy and nothing else from
the package: it is the foundation and depends on nothing above it
(A5).

## 1.2 Helpers

```
function cross_matrix(vector) -> matrix:
    # [v]ₓ such that cross_matrix(v) @ u == cross(v, u)  (Design 1.2)
    (x, y, z) = vector
    return [[ 0, -z,  y],
            [ z,  0, -x],
            [-y,  x,  0]]

function rodrigues(axis, angle) -> matrix:                   # vectorized
    # The right-handed rotation by `angle` about the unit `axis`.
    # `angle` may be a scalar or shape (N,); the result is (3, 3) or
    #   (N, 3, 3).
    cosine = cos(angle); sine = sin(angle)
    outer  = axis ⊗ axis                                    # (3, 3)
    return cosine * IDENTITY + sine * cross_matrix(axis)
           + (1 - cosine) * outer
    # broadcast: scalars cosine/sine against (3, 3), or (N, 1, 1)
    #   against (3, 3) for a sample axis
```

## 1.3 The Frame

```
class Frame:
    axis   unit vector n̂, shape (3,)
    rate   signed scalar Ω; positive is counterclockwise seen from +n̂

    constructor Frame(axis, rate):
        norm = |axis|
        if norm == 0 or not finite: raise ValueError(
            "the frame's axis must be a nonzero vector")
        self.axis = axis / norm
        self.rate = float(rate)
        # No origin field: positions are measured from O on the axis
        #   (Design 1.1, 1.7), and the frame has nothing to add.

    method angle(time) -> scalar or (N,):
        return self.rate * time                               # θ(t) = Ω t

    method angular_velocity(time) -> vector or (N, 3):
        # Ω(t) = Ω n̂, the same in both frames (Design 1.1). `time` is
        #   accepted and ignored so that FD2 changes the body only.
        return self.rate * self.axis, broadcast to time's shape

    method angular_acceleration(time) -> vector or (N, 3):
        return zeros, broadcast to time's shape                # dΩ/dt = 0

    method rotation(time) -> matrix or (N, 3, 3):
        return rodrigues(self.axis, self.angle(time))         # R(t)
```

The four answers of Design 1.1 are these four methods; nothing else
in the package computes an angle, an angular velocity, or a rotation.

## 1.4 The transforms

```
    method to_rotating(time, position_in, velocity_in)
            -> (position_rot, velocity_rot):                  # vectorized
        R      = self.rotation(time)                          # (N, 3, 3)
        omega  = self.angular_velocity(time)                  # (N, 3)
        position_rot = Rᵀ @ position_in                       # (1.1)
        velocity_rot = Rᵀ @ (velocity_in - cross(omega, position_in))
        return position_rot, velocity_rot                     # (1.2)

    method to_inertial(time, position_rot, velocity_rot)
            -> (position_in, velocity_in):                    # vectorized
        R      = self.rotation(time)
        position_in = R @ position_rot
        omega  = self.angular_velocity(time)
        velocity_in = R @ velocity_rot + cross(omega, position_in)
        return position_in, velocity_in

    method launch_to_inertial(position_rot, velocity_rot)
            -> (position_in, velocity_in):
        # A launch given in the rotating frame at t = 0 (Design 1.5):
        #   R(0) = I, so positions coincide and the velocity gains the
        #   rim speed. Equal to to_inertial(0, ...) and kept as its own
        #   name because Design 7.2 cites it.
        return position_rot, velocity_rot + cross(self.rate * self.axis,
                                                  position_rot)
```

`Rᵀ @ v` over a sample axis is `einsum("nji,nj->ni", R, v)`, and
`R @ v` is `einsum("nij,nj->ni", R, v)`; the code writes them so,
with a comment saying which is the transpose, because the two are
the commonest thing to get backwards and the tests of 1.6 would
catch the swap only through the sign check.

## 1.5 What the display asks (Design 1.6)

```
    method rotating_triad_in_inertial(time) -> (3, 3) or (N, 3, 3):
        return self.rotation(time)          # columns: the rotating axes
                                            #   as the room sees them

    method inertial_triad_in_rotating(time) -> (3, 3) or (N, 3, 3):
        return transpose(self.rotation(time))   # columns: the room's
                                                #   axes as the rider
                                                #   sees them
```

The launch point's inertial position, `R(t) r_P`, is
`to_inertial(t, r_P, 0)[0]` and needs no method of its own.

## 1.6 Verification (`tests/unit/test_frame.py`)

Tolerances are `1e-14` unless stated: a handful of products and sums
of order-one numbers, each rounding at `1e-16`.

- `cross_matrix(v) @ u` equals `cross(v, u)` for random `v`, `u`.
- `rodrigues(axis, angle)` for axes `x̂`, `ẑ`, and a random unit
  vector, and angles `0`, `π/2`, `π`, `−π/3`, `1e4`: `R Rᵀ = I`,
  `det R = 1`, `R n̂ = n̂`; `rodrigues(n̂, a) rodrigues(n̂, b) =
  rodrigues(n̂, a + b)`; `rodrigues(ẑ, π/2) x̂ = ŷ` (right-handed).
- `Frame(axis, rate)` normalizes the axis and refuses a zero or
  non-finite one with the message of 1.3; `rate` may be negative.
- `angle`, `angular_velocity`, `angular_acceleration`, and `rotation`
  accept a scalar and a `(N,)` array of times and return the stated
  shapes; `angular_acceleration` is zero.
- Round trip: `to_inertial(t, *to_rotating(t, r, v))` returns `(r, v)`
  for random states and times, and the other way around.
- A particle at rest in the rotating frame, `to_inertial(t, r_rot, 0)`,
  has inertial speed `|rate| |r_⊥|` and velocity along
  `sign(rate) n̂ × r_in` (Design 1.9).
- `|position_rot| = |position_in|` for random inputs.
- `launch_to_inertial(r, v)` equals `to_inertial(0, r, v)`, and for
  a launch toward the axis from the rim of the unit disc the inertial
  velocity's component along `n̂ × r̂` is `rate`.
- **The sign check (Design 1.8, in this module's terms):** with
  `axis = ẑ`, `rate = 1`, and the rotating-frame velocity
  `v_rot = (−sin λ, 0, cos λ)` (north at latitude `λ`), the vector
  `−2 cross(angular_velocity(0), v_rot)` has a positive `y`
  component equal to `2 sin λ`, for `λ` in `{10°, 45°, 80°}`. (The
  term itself is Design 5's; the test here fixes the frame's
  handedness that Design 5 will rely on.)
- Vectorization: `to_rotating` on `(N, 3)` inputs equals, row by
  row, the same call on each row alone.
