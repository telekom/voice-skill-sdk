<template>
  <v-container fluid>
    <v-row>
    <v-col cols="4">
      <v-row>
        <v-card v-if="this.openapi.info" flat>
          <v-card-title>
            {{ this.openapi.info.title }} v{{ this.openapi.info.version }}
            <v-tooltip bottom>
              <template v-slot:activator="{ on, attrs }">
                <v-icon
                    color="primary"
                    dark
                    v-bind="attrs"
                    v-on="on"
                    @click="info"
                >
                  mdi-information
                </v-icon>
              </template>
              <span>Get Skill Info</span>
            </v-tooltip>
          </v-card-title>
          <v-card-text>
            <sub>{{ this.openapi.info.description }}</sub>
          </v-card-text>
        </v-card>
      </v-row>
      <v-row>
        <v-col>
          <v-card flat>
            <v-card-text>Intents</v-card-text>
          </v-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-expansion-panels
              accordion
              focusable
              v-model="intentsPanel"
          > <v-expansion-panel
                v-for="intent in intents" :key="intent.name" @click="select(intent)">
              <v-expansion-panel-header>{{ intent.name }}</v-expansion-panel-header>
              <v-expansion-panel-content>
                <v-row v-for="param in intent.parameters" :key="param.name">
                  <v-col>
                    <v-subheader>{{ param.name }}</v-subheader>
                  </v-col>
                  <v-col>
                    <v-text-field
                        v-model="param.values"
                        :label="param.type"
                        :hint="param.sample"
                        persistent-hint
                        clearable
                        @change="select(intent)"
                        :rules="param.required ? rules : []"
                    ></v-text-field>
                  </v-col>
                  <v-col cols="2">
                    <v-btn icon>
                      <v-icon>mdi-plus</v-icon>
                    </v-btn>
                  </v-col>
                </v-row>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
          <v-card flat>
            <v-card-text>Session</v-card-text>
          </v-card>
          <v-expansion-panels>
            <v-expansion-panel>
              <v-expansion-panel-header v-slot="{ open }">
                <v-row no-gutters>
                  <v-col class="text--secondary">
                    <v-fade-transition leave-absolute>
                      <span v-if="open">Attributes:</span>
                      <v-row
                          v-else
                          style="width: 100%"
                      >
                        <v-col cols="4">
                          attrs: {{ session.attributes && '{...}' || 'Not set' }}
                        </v-col>
                        <v-col cols="4">
                          id: {{ session.id || 'Not set' }}
                        </v-col>
                        <v-col cols="4">
                          new: {{ session.new || 'Not set' }}
                        </v-col>
                      </v-row>
                    </v-fade-transition>
                  </v-col>
                </v-row>
              </v-expansion-panel-header>
              <v-expansion-panel-content>
                <v-row>
                  <v-row
                      v-for="attr in session.attributes"
                      :key="attr.key"
                      justify="space-around"
                  >
                    <v-col cols="3">
                      <v-text-field
                          v-model="attr.key"
                          label="Name"
                          @change="intentsPanel !== null && select(intents[intentsPanel])"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="3">
                      <v-text-field
                          v-model="attr.value"
                          label="Value"
                          @change="intentsPanel !== null && select(intents[intentsPanel])"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="1">
                      <v-btn icon>
                        <v-icon>mdi-plus</v-icon>
                      </v-btn>
                    </v-col>
                  </v-row>
                  <v-row
                      justify="space-around"
                  >
                    <v-col cols="3">
                      <v-text-field
                          clearable
                          v-model="session.id"
                          label="id"
                          @change="intentsPanel !== null && select(intents[intentsPanel])"
                      ></v-text-field>
                    </v-col>

                    <v-col cols="3">
                      <v-checkbox
                          v-model="session.new"
                          label="new"
                          @change="intentsPanel !== null && select(intents[intentsPanel])"
                      ></v-checkbox>
                    </v-col>
                    <v-col cols="1">
                    </v-col>
                  </v-row>
                </v-row>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>
      </v-row>
    </v-col>
    <v-col>
      <v-row>
        <v-col>
          <v-form>
            <v-textarea
                v-model="request"
                outlined
                label="Request"
                required
                :rules="[v => this.validate(v) || 'Request must be valid JSON!']"
                rows="10"
                class="v-textarea-json"
            ></v-textarea>
          </v-form>
        </v-col>
        <v-col>
          <v-textarea
              v-model="response"
              readonly
              outlined
              label="Response"
              rows="10"
              class="v-textarea-json"
          ></v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-textarea
              v-model="log"
              readonly
              filled
              outlined
              label="Log"
              id="log"
          ></v-textarea>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-btn @click="submit">Submit</v-btn>
        </v-col>
      </v-row>
    </v-col>
    </v-row>
  </v-container>
</template>
<script>

export default {

  data: () => ({
      openapi: {},
      intents: {},
      session: {
        id: 123,
        new: true,
        attributes: [{
          key: "attr-1",
          value: "value-1"
        }],
      },
      request: "{}",
      response: "",
      connection: null,
      log: "",
      intentsPanel: null,
      rules: [
          value => !!value || "Field required!",
          value => value instanceof Array ?
              value.length > 0 :
              (value || '').trim().length > 0
              || "Non-blank value required!" ,
      ],
  }),

  created: function() {
      this.getAPIDescription();
      this.getIntents();
      this.connectLogs();
  },

  methods: {
      validate(input) {
        try {
          JSON.parse(input)
          return true
        } catch (e) {
          return false
        }
      },
      submit() {
        const paths = this.openapi.paths
        const p = Object.keys(paths).filter(
            k => paths[k]["post"] && paths[k]["post"].summary.endsWith("Intent")
        )[0]
        const data = JSON.parse(this.request)
        const panel = this.intentsPanel
        this.axios.post('http://localhost:4242' + p, data).then(
            r => {
              this.response = JSON.stringify(r.data, null, 2)
              // Update session attributes
              const session = r.data?.session
              if (session) {
                this.session.attributes = Object.entries(session.attributes).map(([key, value]) => ({key, value}))
              }
              // Redraw request if intent is selected
              if (Number.isInteger(panel)) {
                this.select(this.intents[panel])
              }
            }
        ).catch(err => this.response = err)
      },
      select(intent) {
        const attributes = Object.fromEntries(intent.parameters.filter(
            e => e.values instanceof Array ? e.values.length > 0 : e.values != null).map(
                e => [e.name, e.values instanceof Array ? e.values : [e.values]]
        ))
        const attrV2 = (value) => Object({
          id: 0,
          nestedIn: [],
          overlapsWith: [],
          value: value,
          extras: {},
        })
        const attributesV2 = Object.fromEntries(intent.parameters.filter(
            e => e.values instanceof Array ? e.values.length > 0 : e.values != null).map(
                e => [e.name, e.values instanceof Array ? e.values.map(e => attrV2(e)) : [attrV2(e.values)]]
        ))
        this.request = JSON.stringify({
          context: {
            intent: intent.name,
            locale: "de",
            attributes: attributes,
            attributesV2: attributesV2,
            configuration: {},
            tokens: {},
          },
          session: {
            id: this.session.id,
            attributes: Object.fromEntries(this.session.attributes.map(e => [e.key, e.value])),
            new: this.session.new,
          },
          spiVersion: 1.2,
        }, null, 2)
      },
      info() {
        const paths = this.openapi.paths
        const p = Object.keys(paths).filter(
            k => paths[k]["get"] && paths[k]["get"].summary.endsWith("Info")
        )[0]
        this.axios.get('http://localhost:4242' + p).then(
            r => this.response = JSON.stringify(r.data, null, 2)
        ).catch(err => this.response = err)
      },
      getIntents() {
          const uri = 'http://localhost:4242/intents'
          this.axios.get(uri).then(
              r => this.intents = r.data
          )
      },
      getAPIDescription() {
          const uri = 'http://localhost:4242/openapi.json'
          this.axios.get(uri).then(
              r => this.openapi = r.data
          )
      },
      connectLogs() {

          this.connection = new WebSocket("ws://localhost:4242/logs");

          const self = this
          this.connection.onmessage = function(event) {
            const container = document.getElementById ( "log" )
            container.scrollTop = container.scrollHeight
            self.log += JSON.parse(event.data).msg + "\n"
          }

          this.connection.onopen = function(event) {
            console.log(event)
            console.log("Successfully connected to the logs server...")
          }
      },

  }
};
</script>

<style scoped>
.v-expansion-panel-content .row:first-child {
  margin-top: 12px;
}
.v-textarea-json {
  font-family: Monaco,Menlo,Consolas,Bitstream Vera Sans Mono,monospace;
}
</style>