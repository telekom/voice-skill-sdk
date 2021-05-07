<template>
  <v-app>
      <v-tabs>
        <v-tab>Design</v-tab>
        <v-tab>Test</v-tab>
        <v-tab-item>
          <DesignIntent/>
        </v-tab-item>
        <v-tab-item>
          <TestIntent/>
        </v-tab-item>
      </v-tabs>
  </v-app>
</template>

<script>
import DesignIntent from './components/DesignIntent';
import TestIntent from './components/TestIntent';

export default {
  name: 'App',

  components: {
    DesignIntent,
    TestIntent,
  },

  data: () => ({
    //
  }),
};
</script>
