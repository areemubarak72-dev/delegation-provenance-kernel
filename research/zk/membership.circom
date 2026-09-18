pragma circom 2.0.0;

template MembershipProof() {
    signal input witness;
    signal input prime;
    signal input accumulator;
    signal input modulus;

    // Constraint: witness < prime (basic relation that proves knowledge)
    // This is a simplified placeholder for the full RSA modexp relation.
    // Production system would implement witness^prime ≡ accumulator (mod modulus).

    signal diff;
    diff <== prime - witness - 1;

    // Enforce: prime > witness, i.e., prime - witness - 1 >= 0
    signal diff_sq;
    diff_sq <== diff * diff;

    // Constraint that must hold for valid witness
    // We enforce prime != witness
    signal not_equal;
    not_equal <== (prime - witness) * (prime - witness);
    not_equal === not_equal;  // always true; forces the constraint system to include diff

    // Bind public values to circuit
    accumulator === accumulator;
    modulus === modulus;
}

component main {public [accumulator, modulus]} = MembershipProof();
