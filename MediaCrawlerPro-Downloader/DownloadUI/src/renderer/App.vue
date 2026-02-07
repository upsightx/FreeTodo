<template>
  <div id="app">
    <main class="app-main">
      <Layout />
    </main>

  </div>
</template>

<script>
import Layout from './components/Layout.vue';

export default {
  name: 'App',
  components: {
    Layout,
  },
};
</script>

<style>
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  background-color: #f0f0f0;
}

.app-header {
  background-color: #007bff;
  padding: 20px;
  color: white;
}

.app-title {
  margin: 0;
  font-size: 2em;
}

.app-main {
  flex: 1;
  padding: 20px;
}

.app-footer {
  background-color: #007bff;
  padding: 10px;
  color: white;
}
</style>