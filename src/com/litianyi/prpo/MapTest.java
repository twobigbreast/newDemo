package com.litianyi.prpo;

import java.util.HashMap;
import java.util.Map;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/26 10:32
 * @Description:
 */
public class MapTest {
    public static void main(String[] args) {
        Map<String, String> map = new HashMap<>();
        map.put("哈哈","呵呵");
        map.putIfAbsent("哈哈","ee");
        System.out.println(map);
    }
}
