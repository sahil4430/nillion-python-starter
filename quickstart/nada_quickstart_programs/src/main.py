from nada_dsl import *

def nada_main():
    # Define parties involved in the computation
    party1 = Party(name="Party1")
    party2 = Party(name="Party2")
    party3 = Party(name="Party3")

    # Create inputs for the secret integers from the respective parties
    secret_input_a = SecretInteger(Input(name="A", party=party1))
    secret_input_b = SecretInteger(Input(name="B", party=party2))

    # Perform the addition operation on the secret inputs
    computation_result = secret_input_a + secret_input_b

    # Define the output of the computation to be sent to party3
    return [Output(computation_result, "my_output", party3)]
