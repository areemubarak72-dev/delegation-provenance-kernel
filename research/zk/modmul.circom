pragma circom 2.0.0;

// Proves knowledge of a, b such that:
//     a * b = q * modulus + c
// where c is a public value, without revealing a, b, or q.
//
// This is the core modular multiplication primitive used
// in RSA accumulators.

template ModMul() {
    signal input a;      // private
    signal input b;      // private
    signal input q;      // private (quotient)
    signal input modulus; // public
    signal input c;      // public (result)

    // Constraint: a * b == q * modulus + c
    signal lhs;
    lhs <== a * b;

    signal rhs;
    rhs <== q * modulus + c;

    lhs === rhs;
}

component main {public [modulus, c]} = ModMul();
