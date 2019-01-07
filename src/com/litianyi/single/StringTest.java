package com.litianyi.single;

/**
 * @Auther: ICC18e697
 * @Date: 2018/11/23 10:48
 * @Description:
 */
public class StringTest {
    public static void main(String[] args) {
        String s="a0a00702-d219-4c7d-853e-a915fb9eb082";
        String s1 = s.replaceAll("-", "").toUpperCase();
        System.out.println(s1);
    }
}
