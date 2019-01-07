package com.litianyi.queue;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/26 10:14
 * @Description:
 */
public class VolatitleTest {

    private static volatile String now;

    private static volatile String yesterday;

    public static void main(String[] args) {
        System.out.println(now);
        System.out.println(yesterday);
    }
}
