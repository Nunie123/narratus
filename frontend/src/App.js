import React, { Component } from 'react';
import './App.css';

class App extends Component {
  render() {
    return (
      <div className="App">
        {header}
      </div>
    );
  }
}

const header = (
  <header className="grid-container">
    <ul className="nav-list-left">
      <li className="logo nav-left"><a href="#">narratus</a></li>
      <li className="nav-left"><a href="#">Connections</a></li>
      <li className="nav-left"><a href="#">Datasets</a></li>
      <li className="nav-left"><a href="#">Charts</a></li>
      <li className="nav-left"><a href="#">Reports</a></li>
      <li className="nav-right"><a href="#">Settings</a></li>
      <li className="nav-right"><a href="#">Login</a></li>
    </ul>
  </header>
)




export default App;
