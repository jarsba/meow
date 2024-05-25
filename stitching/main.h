class SumClass {

public:

    SumClass( double a_in, double b_in, int N_in)
    {
        a = a_in;
        b = b_in;
    }

    void run()
    {
        sum = a + b;
        return sum;
    }
};